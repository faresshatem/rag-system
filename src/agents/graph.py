import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver
from redis import Redis

from src.agents.state import AgentState
from src.agents.supervisor import supervisor_node
from src.agents.planning import query_planning_node

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Query-Planning_Agent", query_planning_node)
    
    workflow.add_node("Retrieval_Agent", lambda state: {"next_agent": "Supervisor", "is_context_valid": True})
    workflow.add_node("Synthesis_Agent", lambda state: {"next_agent": "END"})

    workflow.add_edge(START, "Supervisor")
    
    def router(state: AgentState):
        if state.next_agent == "END":
            return END
        return state.next_agent
        
    workflow.add_conditional_edges("Supervisor", router)
    
    workflow.add_edge("Query-Planning_Agent", "Supervisor")
    workflow.add_edge("Retrieval_Agent", "Supervisor")
    workflow.add_edge("Synthesis_Agent", END)
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = Redis.from_url(redis_url)
    memory = RedisSaver(redis_client=redis_conn)
    memory.setup()
    app = workflow.compile(checkpointer=memory)
    return app

if __name__ == "__main__":
    app = build_graph()
    
    config = {"configurable": {"thread_id": "test_session_12"}}
    
    initial_state = {
        "messages": [{"role": "user", "content": "I need to know my allowed remote days and check my laptop request status."}],
        "allowed_domains": ["HR", "IT"],
        "step_count": 0
    }
    
    for event in app.stream(initial_state, config=config):
        for key, value in event.items():
            print(f"\n--- Output from {key} ---")
            print({k: v for k, v in value.items() if v is not None})