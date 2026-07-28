from src.agents.state import AgentState

async def memory_summarization_node(state: AgentState) -> dict:
    """Keeps the current conversation summary available to the graph."""
    return {
        "conversation_summary": state.conversation_summary or ""
    }
