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
from src.agents.retrieval import retrieval_node
from src.agents.verification import verification_node
from src.agents.synthesis import synthesis_node
from src.agents.casual_chat import casual_chat_node
from src.agents.intent_router import intent_router_node
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
    finished_tasks = [t for t in state.tasks if t.status in ('completed', 'failed', 'skipped')]
    
    if finished_tasks:
        summaries = [str(t.result_summary) for t in finished_tasks if t.result_summary]
        final_answer = "Based on the retrieved policies and database lookups:\n" + "\n\n".join(summaries)
    else:
        final_answer = "I couldn't find any specific answers for your query, but how can I help you generally?"
        
    return {
        "next_agent": "END",
        "answer": final_answer
    }




async def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add Real Nodes
    workflow.add_node("Intent_Router_Agent", intent_router_node)
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Query-Planning_Agent", query_planning_node)
    workflow.add_node("Structured_Data_Agent", structured_data_node)
    
    # 2. Add Nodes
    workflow.add_node("Retrieval_Agent", mock_retrieval_node)
    workflow.add_node("Verification_Agent", mock_verification_node)
    workflow.add_node("Synthesis_Agent", mock_synthesis_node)
    workflow.add_node("Casual_Chat_Agent", casual_chat_node)

    # 3. Entry Point
    workflow.add_edge(START, "Intent_Router_Agent")
    
    # 4. Supervisor Routing Logic
    def router(state: AgentState):
        if state.next_agent == "END":
            return END
        return state.next_agent
        
    workflow.add_conditional_edges("Intent_Router_Agent", router)
    workflow.add_conditional_edges("Supervisor", router)
    workflow.add_conditional_edges("Query-Planning_Agent", router)
    
    # 5. Fixed Edges 
    workflow.add_edge("Structured_Data_Agent", "Verification_Agent")
    workflow.add_edge("Retrieval_Agent", "Verification_Agent")
    workflow.add_edge("Verification_Agent", "Supervisor")
    workflow.add_edge("Synthesis_Agent", END)
    workflow.add_edge("Casual_Chat_Agent", END)
    
    # 6. Memory Setup
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = AsyncRedis.from_url(redis_url)
    memory = AsyncRedisSaver(redis_client=redis_conn)
    await memory.setup()
    
    app = workflow.compile(checkpointer=memory)
    return app