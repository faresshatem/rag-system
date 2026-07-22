import asyncio
from src.agents.state import AgentState, Message
from src.agents.casual_chat import casual_chat_node

# Simulate a state that already has a summary
summary_content = "Summary of previous conversation:\nMohaned asked about 2+2 (it is 4) and the CEO of Apple (Tim Cook)."

state = AgentState(
    messages=[Message(role="user", content="Hello!")],
    casual_chat_history=[Message(role="system", content=summary_content)],
    tasks=[], current_task_id=None, next_agent="Casual_Chat_Agent", query_intent="casual_chat", answer="", username="test"
)

res = casual_chat_node(state)
print("Answer:", res['answer'])

