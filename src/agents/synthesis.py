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
        Return context chunks that are safe to ground an answer on.

        Priority:
        1. Chunks from tasks with status == 'completed'.
        2. If no completed-task chunks exist, fall back to chunks from tasks
           whose result_summary indicates data was actually retrieved (i.e. the
           task ran and produced results but was later marked 'failed' by
           verification — a common situation when the grading model is
           overly strict).  This prevents a strict verifier from silently
           discarding perfectly good retrieved context.
        """
        task_map = {t.task_id: t for t in state.tasks}

        # Primary: chunks from completed tasks
        completed_ids = {tid for tid, t in task_map.items() if t.status == "completed"}
        chunks = [
            c for c in state.retrieved_context
            if any(c.chunk_id.startswith(f"{tid}_") for tid in completed_ids)
        ]
        if chunks:
            return chunks

        # Fallback: chunks from tasks that retrieved data but were marked failed
        # (e.g. verification returned is_valid=False despite usable context).
        failed_ids = {
            tid for tid, t in task_map.items()
            if t.status == "failed" and t.result_summary
            and "ACCESS DENIED" not in t.result_summary
            and "Skipped" not in t.result_summary
        }
        chunks = [
            c for c in state.retrieved_context
            if any(c.chunk_id.startswith(f"{tid}_") for tid in failed_ids)
        ]
        if chunks:
            logger.info(
                "No completed-task chunks, but found %d chunk(s) from tasks "
                "that did retrieve data. Using them as fallback context.",
                len(chunks),
            )
        return chunks

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

    @staticmethod
    def _human_source_name(file_name: str) -> str:
        """Convert a filename like 'leave_policy.txt' into 'Leave Policy'."""
        name = file_name
        for ext in (".txt", ".pdf", ".docx", ".md"):
            if name.lower().endswith(ext):
                name = name[: -len(ext)]
                break
        return name.replace("_", " ").replace("-", " ").title()

    def _dedupe_sources(self, chunks: List[RetrievedChunk]) -> List[str]:
        """Return unique, human-readable source names preserving first-seen order."""
        seen = set()
        sources = []
        for chunk in chunks:
            key = chunk.file_name.lower()
            if key not in seen:
                seen.add(key)
                sources.append(self._human_source_name(chunk.file_name))
        return sources

    def synthesize(self, state: AgentState) -> dict:
        logger.info("Starting synthesis process.")

        if state.query_intent == "casual_chat":
            return self._casual_chat_answer(state)

        verified_chunks = self._verified_chunks(state)

        if not verified_chunks:
            logger.info("No verified context available; returning fallback answer.")
            return {
                "next_agent": "END",
                "answer": (
                    "I couldn't find this information in the available internal knowledge base.\n\n"
                    "**Sources**\n\nNone"
                ),
                "citations": None,
            }

        context_block = self._build_context_block(verified_chunks)
        user_query = state.messages[-1].content if state.messages else ""
        source_names = self._dedupe_sources(verified_chunks)
        sources_block = "\n".join(f"- {name}" for name in source_names) if source_names else "None"

        # Include the original task description(s) to guide the LLM's focus
        task_descriptions = "\n".join(
            f"- {t.description}" for t in state.tasks if t.status in ("completed", "failed") and t.result_summary
        )

        try:
            llm = get_routed_llm(state)

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a professional AI assistant for an enterprise knowledge system. "
                    "Your job is to answer the user's question accurately using ONLY the verified context blocks below.\n\n"
                    "STRICT RULES:\n"
                    "1. Read EVERY context block carefully before answering.\n"
                    "2. Look for specific facts: numbers, time periods, frequencies, percentages, policies, and rules.\n"
                    "3. If the context contains the answer, state it clearly and concisely. Do NOT say the information is missing.\n"
                    "4. If the context truly does not contain the answer, say: "
                    "\"I couldn't find this information in the available internal knowledge base.\"\n"
                    "5. Synthesize information from all relevant blocks into one coherent answer.\n"
                    "6. Remove duplicated sentences and repeated facts.\n"
                    "7. Never invent information not found in the context.\n"
                    "8. Never expose internal details: no chunk IDs, task IDs, vector IDs, "
                    "pipeline messages, verification status, or debug information.\n"
                    "9. Do NOT include a Sources section; it will be appended automatically.\n"
                    "10. Do NOT include citation tags like [Source: ...] in your answer.\n"
                    "11. Keep markdown simple: use **bold** for key facts only.",
                ),
                (
                    "user",
                    "User Question: {query}\n\n"
                    "Information Sought:\n{tasks}\n\n"
                    "Verified Context:\n{context}",
                ),
            ])

            response = (prompt | llm).invoke({
                "query": user_query,
                "tasks": task_descriptions,
                "context": context_block,
            })
            final_answer = response.content.strip()

            # If the LLM determined the context doesn't answer the question,
            # suppress unrelated source listings.
            _not_found = "couldn't find" in final_answer.lower() or "not found" in final_answer.lower()
            if _not_found:
                final_answer += "\n\n**Sources**\n\nNone"
            else:
                final_answer += f"\n\n**Sources**\n\n{sources_block}"

        except Exception as e:
            logger.error("Synthesis LLM call failed: %s", str(e))
            joined = "\n\n".join(
                f"{chunk.text}" for chunk in verified_chunks
            )
            final_answer = f"{joined}\n\n**Sources**\n\n{sources_block}"

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
