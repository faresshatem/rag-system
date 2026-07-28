from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from src.generation.generator import api_llm



class JudgeResult(BaseModel):
    faithfulness: float = Field(
        description="Score between 0 and 1 indicating whether the answer is supported by the retrieved context."
    )

    relevance: float = Field(
        description="Score between 0 and 1 indicating whether the answer addresses the user's question."
    )

    citation_accuracy: float = Field(
        description="Score between 0 and 1 indicating whether citations support the answer."
    )

    completeness: float = Field(
        description="Score between 0 and 1 indicating whether important information is missing."
    )

    hallucination_risk: float = Field(
        description="Score between 0 and 1 where 0 means no hallucination."
    )

    overall_score: float = Field(
        description="Overall quality score."
    )

    reasoning: str = Field(
        description="Short explanation describing the assigned scores."
    )


class LLMJudge:

    def __init__(self):

        self.system_prompt = """
You are an Enterprise RAG Evaluation Judge.

Your ONLY responsibility is to evaluate the generated answer.

Never rewrite the answer.

Evaluate ONLY.

Evaluation Criteria:

1. Faithfulness
Is every claim supported by the retrieved context?

2. Relevance
Does the answer answer the user's question?

3. Citation Accuracy
Do the citations support the answer?

4. Completeness
Is important information missing?

5. Hallucination Risk
Estimate hallucination probability.

Return ONLY the requested JSON.
"""

    def evaluate(
        self,
        question: str,
        answer: str,
        retrieved_context: str,
        citations: Optional[List] = None,
        golden_answer: Optional[str] = None,
    ) -> JudgeResult:

        structured_llm = api_llm.with_structured_output(JudgeResult)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                (
                    "user",
                    """
Question:

{question}

Retrieved Context:

{context}

Generated Answer:

{answer}

Golden Answer:

{golden}

Citations:

{citations}
""",
                ),
            ]
        )

        chain = prompt | structured_llm

        citation_text = ""

        if citations:
            citation_text = "\n".join(
                [
                    f"{c.source_file} | page={c.page}"
                    for c in citations
                ]
            )

        result: JudgeResult = chain.invoke(
            {
                "question": question,
                "context": retrieved_context,
                "answer": answer,
                "golden": golden_answer or "Not Provided",
                "citations": citation_text,
            }
        )

        return result


judge = LLMJudge()