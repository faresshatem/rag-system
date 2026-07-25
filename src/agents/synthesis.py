import logging
import re
from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate

from src.agents.state import AgentState, Citation, RetrievedChunk
from src.generation.router import get_routed_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynthesisAgent:
    """
    The Synthesis Agent generates the final, user-facing answer using an LLM,
    grounded ONLY on the context chunks that survived verification (i.e. chunks
    that belong to tasks which completed successfully — not tasks that failed
    verification, were skipped, or were denied by RBAC). Every factual claim is
    tied back to its source via a Markdown citation of the form
    `[Source: <file_name> | Chunk: #<chunk_id>]`.
    """

    def _verified_chunks(self, state: AgentState) -> List[RetrievedChunk]:
        """
        Only chunks produced by tasks with status == 'completed' are considered
        verified context. Chunks from 'failed'/'skipped' tasks (verification
        failures, RBAC denials, unmet conditions, etc.) are excluded from
        synthesis so the model never grounds an answer on rejected context.
        """
        completed_task_ids = {t.task_id for t in state.tasks if t.status == "completed"}
        return [
            chunk
            for chunk in state.retrieved_context
            if any(chunk.chunk_id.startswith(f"{tid}_") for tid in completed_task_ids)
        ]

    def _read_task_notes(self, state: AgentState) -> List[str]:
        """Human-readable notes for tasks that produced no citable chunks (e.g. RBAC denials, skips)."""
        notes = []
        for t in state.tasks:
            if t.status in ("failed", "skipped") and t.result_summary:
                notes.append(f"- {t.description}: {t.result_summary}")
        return notes

    def _build_context_block(self, chunks: List[RetrievedChunk]) -> str:
        """Render numbered, citation-tagged context blocks for the synthesis prompt."""
        lines = []
        for idx, chunk in enumerate(chunks, start=1):
            page_info = f" | Page: {chunk.page}" if chunk.page is not None else ""
            citation_tag = f"[Source: {chunk.file_name} | Chunk: #{chunk.chunk_id}{page_info}]"
            lines.append(f"[{idx}] {citation_tag}\n{chunk.text}")
        return "\n\n".join(lines)

    def _build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Structured Citation objects mirroring every source made available to the LLM."""
        return [
            Citation(
                span=chunk.text[:200],
                source_file=chunk.file_name,
                chunk_id=chunk.chunk_id,
                page=chunk.page,
            )
            for chunk in chunks
        ]

    def _dedupe_by_source(self, chunks: List[RetrievedChunk]) -> Dict[str, RetrievedChunk]:
        return {chunk.chunk_id: chunk for chunk in chunks}

    def _casual_chat_answer(self, state: AgentState) -> dict:
        """
        Pure conversational / general-knowledge queries (greetings, small talk,
        or anything the Planning Agent classified as 'casual_chat') carry no
        tasks and no retrieved_context by design. Answer directly with the LLM
        instead of falling into the "no verified context" RAG-refusal path,
        since there was never supposed to be domain context for these.
        """
        user_query = state.messages[-1].content if state.messages else ""
        try:
            llm = get_routed_llm(state)
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a helpful, polite AI assistant for an Enterprise RAG system. "
                    "The user's message is casual conversation or a general-knowledge question "
                    "unrelated to the company's internal HR/IT data. Respond naturally and helpfully. "
                    "Do not claim to have searched, or refuse to answer, or mention internal documents "
                    "or databases for this kind of message.",
                ),
                ("user", "{query}"),
            ])
            response = (prompt | llm).invoke({"query": user_query})
            return {"next_agent": "END", "answer": response.content, "citations": None}
        except Exception as e:
            logger.error("Casual-chat synthesis failed: %s", str(e))
            return {"next_agent": "END", "answer": "Hi! How can I help you today?", "citations": None}

    def synthesize(self, state: AgentState) -> dict:
        logger.info("Starting synthesis process.")

        if state.query_intent == "casual_chat":
            return self._casual_chat_answer(state)

        verified_chunks = self._verified_chunks(state)
        blocked_notes = self._read_task_notes(state)

        if not verified_chunks:
            fallback = (
                "I couldn't find verified information to answer your request."
                if not blocked_notes
                else "I couldn't retrieve the information you need:\n" + "\n".join(blocked_notes)
            )
            logger.info("No verified context available; returning fallback answer without LLM call.")
            return {"next_agent": "END", "answer": fallback, "citations": None}

        context_block = self._build_context_block(verified_chunks)
        user_query = state.messages[-1].content if state.messages else ""

        try:
            llm = get_routed_llm(state)

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are the Synthesis & Citation Agent for an Enterprise RAG system. "
                    "Answer the user's question using ONLY the numbered context blocks provided below. "
                    "Never use outside knowledge and never invent facts that are not in the context. "
                    "After every sentence or claim that relies on a specific context block, append that "
                    "block's exact citation tag in Markdown, verbatim, e.g. "
                    "'Employees get 14 days of leave [Source: hr_policy.pdf | Chunk: #12].' "
                    "If the context blocks conflict or are insufficient to fully answer, say so explicitly. "
                    "Write a clear, concise, well-structured answer in Markdown.",
                ),
                (
                    "user",
                    "User Question: {query}\n\nContext:\n{context}",
                ),
            ])

            response = (prompt | llm).invoke({"query": user_query, "context": context_block})
            final_answer = response.content

            if blocked_notes:
                final_answer += "\n\n> Note: some parts of your request could not be completed:\n" + "\n".join(
                    f"> {n}" for n in blocked_notes
                )

        except Exception as e:
            logger.error("Synthesis LLM call failed: %s", str(e))
            # Fail safe: fall back to a plainly-cited concatenation of verified context
            # rather than surfacing a raw error to the user.
            joined = "\n\n".join(
                f"{chunk.text} [Source: {chunk.file_name} | Chunk: #{chunk.chunk_id}]"
                for chunk in verified_chunks
            )
            final_answer = f"Based on the retrieved context:\n\n{joined}"

        citations = self._build_citations(list(self._dedupe_by_source(verified_chunks).values()))

        logger.info(
            "Synthesis completed. %d verified chunk(s) used, %d citation(s) produced.",
            len(verified_chunks),
            len(citations),
        )

        return {
            "next_agent": "END",
            "answer": final_answer,
            "citations": citations,
        }


_synthesis_agent = SynthesisAgent()


def synthesis_node(state: AgentState) -> dict:
    """LangGraph node wrapper around SynthesisAgent.synthesize()."""
    print("\n[Synthesis Agent] Generating final cited answer from verified context...")
    return _synthesis_agent.synthesize(state)
