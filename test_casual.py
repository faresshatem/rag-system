from src.agents.state import AgentState, Message
from src.agents.casual_chat import casual_chat_node
import asyncio
import os
os.environ["TAVILY_API_KEY"] = "tvly-DUMMYKEY"
state = AgentState(messages=[Message(role="user", content="Hello")], tasks=[], current_task_id=None, next_agent="Casual_Chat_Agent", query_intent="casual_chat", answer="", username="test")
res = casual_chat_node(state)
print(res)
