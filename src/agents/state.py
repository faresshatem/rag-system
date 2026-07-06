from typing import Annotated, Sequence
from typing_extensions import TypedDict
import operator
from langchain_core.messages import BaseMessage

class AgenticRAGState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    allowed_domain: str
    retrieved_context: str
    is_context_valid: bool
    step_count: int
