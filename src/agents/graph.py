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
from src.agents.memory import memory_summarization_node

load_dotenv(find_dotenv())

async def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add Real Nodes
    workflow.add_node("Memory_Agent", memory_summarization_node) 
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Query-Planning_Agent", query_planning_node)
    workflow.add_node("Structured_Data_Agent", structured_data_node)

    workflow.add_node("Retrieval_Agent", retrieval_node)
    workflow.add_node("Verification_Agent", verification_node)
    workflow.add_node("Synthesis_Agent", synthesis_node)

    workflow.add_edge(START, "Memory_Agent")
    workflow.add_edge("Memory_Agent", "Supervisor")
    
    # 4. Supervisor Routing Logic
    def router(state: AgentState):
        if state.next_agent == "END":
            return END
        return state.next_agent
        
    workflow.add_conditional_edges("Supervisor", router)
    
    # 5. Fixed & Conditional Edges 
    def planner_router(state: AgentState):
        if state.query_intent in ["casual_chat", "out_of_scope", "ready_for_synthesis"]:
            return "Synthesis_Agent"
        return "Supervisor"

    workflow.add_conditional_edges("Query-Planning_Agent", planner_router)
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