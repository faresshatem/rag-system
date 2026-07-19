import os
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import AsyncRedisSaver
from redis.asyncio import Redis as AsyncRedis
from dotenv import load_dotenv, find_dotenv
from src.agents.state import AgentState
from src.agents.supervisor import supervisor_node
from src.agents.planning import query_planning_node
from src.agents.structured import structured_data_node 
import uuid

load_dotenv(find_dotenv())

def mock_retrieval_node(state: AgentState):
    print("\n[Mock Retrieval] Simulating vector search...")
    updated_tasks = list(state.tasks)
    
    for t in updated_tasks:
        if t.task_id == state.current_task_id:
            t.status = "completed"
            
            if t.target_domain == 'HR':
                t.result_summary = "HR Policy found: Employees can take up to 14 consecutive days of ANNUAL leave with direct manager approval."
            elif t.target_domain == 'IT':
                t.result_summary = "IT Policy found: RESOLVED tickets will be permanently closed after 48 hours of inactivity."
            else:
                t.result_summary = "Policy found: Standard company guidelines apply."
                
    return {
        "tasks": updated_tasks,
        "current_task_id": None, 
        "next_agent": "Verification_Agent"
    }
def mock_verification_node(state: AgentState):
    print("\n[Mock Verification] Checking retrieved data...")
    
    updated_tasks = list(state.tasks)
    
    active_task = next((t for t in updated_tasks if t.task_id == state.current_task_id), None)
    
    if active_task and active_task.status == 'completed':
        
        if "No records found" in str(active_task.result_summary):
            print("   -> [Verification Failed] Database returned empty. Sending feedback.")
            return {
                "tasks": updated_tasks,
                "is_context_valid": False, 
                "next_agent": "Supervisor"
            }
            
        if "Mocked context" in str(active_task.result_summary):
            print("   -> [Verification Failed] Useless vector data found. Sending feedback.")
            return {
                "tasks": updated_tasks,
                "is_context_valid": False, 
                "next_agent": "Supervisor"
            }
            
    print("   -> [Verification Passed] Data looks good. Approving.")
    return {
        "is_context_valid": True, 
        "next_agent": "Supervisor"
    }

def mock_synthesis_node(state: AgentState):
    print("\n[Mock Synthesis] Generating final text based on everything...")
    return {
        "next_agent": "END"
    }


async def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add Real Nodes
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Query-Planning_Agent", query_planning_node)
    workflow.add_node("Structured_Data_Agent", structured_data_node)
    
    # 2. Add Mock Nodes
    workflow.add_node("Retrieval_Agent", mock_retrieval_node)
    workflow.add_node("Verification_Agent", mock_verification_node)
    workflow.add_node("Synthesis_Agent", mock_synthesis_node)

    # 3. Entry Point
    workflow.add_edge(START, "Supervisor")
    
    # 4. Supervisor Routing Logic
    def router(state: AgentState):
        if state.next_agent == "END":
            return END
        return state.next_agent
        
    workflow.add_conditional_edges("Supervisor", router)
    
    # 5. Fixed Edges 
    workflow.add_edge("Query-Planning_Agent", "Supervisor")
    workflow.add_edge("Structured_Data_Agent", "Verification_Agent")
    workflow.add_edge("Retrieval_Agent", "Verification_Agent")
    workflow.add_edge("Verification_Agent", "Supervisor")
    workflow.add_edge("Synthesis_Agent", END)
    
    # 6. Memory Setup
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = AsyncRedis.from_url(redis_url)
    memory = AsyncRedisSaver(redis_client=redis_conn)
    await memory.setup()
    
    app = workflow.compile(checkpointer=memory)
    return app


async def main():
    app = await build_graph()
    
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}
    print(f"Starting new chat session with thread_id: {session_id}")
    
    initial_state = {
        "messages": [{"role": "user", "content": "hi , how are you ? tell me about ai"}],
        "allowed_domains": ["HR","IT"],
        "step_count": 0,
        "tasks": []
    }
  
    print("🚀 Starting Local Graph Execution...\n" + "="*40)
    
    async for event in app.astream(initial_state, config=config):
        for key, value in event.items():
            print(f"\n🟢 --- Output from Node: {key} ---")
            
            for k, v in value.items():
                if v is not None and k not in ["messages", "retrieved_context"]: 
                    print(f"   ➤ {k}: {v}")
                elif k == "retrieved_context" and v:
                    print(f"   ➤ retrieved_context: [List containing {len(v)} chunk(s)]")

if __name__ == "__main__":
    asyncio.run(main())