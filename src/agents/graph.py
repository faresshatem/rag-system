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
from src.generation.router import get_routed_llm
from langchain_core.prompts import ChatPromptTemplate
from src.agents.memory import memory_summarization_node
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
    print("\n[Synthesis Agent] Generating final intelligent response...")
    llm = get_routed_llm(state)
    
    finished_tasks = [t for t in state.tasks if t.status in ('completed', 'failed', 'skipped')]
    task_results = "\n\n".join([str(t.result_summary) for t in finished_tasks if t.result_summary])
   
    chat_history = "\n".join([f"{m.role}: {m.content}" for m in state.messages[-4:]]) if state.messages else ""
    
    user_query = state.messages[-1].content if state.messages else ""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the final Synthesis Agent for an Enterprise RAG system (HR & IT).
        Your job is to provide a polite, professional, and highly accurate response in the SAME LANGUAGE as the user.
        
        AVAILABLE DATA FROM DATABASES/POLICIES:
        {task_results}
        
        RECENT CHAT HISTORY:
        {chat_history}
        
        RULES:
        1. If the user's query requires internal data, use ONLY the 'AVAILABLE DATA' to formulate your answer.
        2. META-QUESTIONS: If the user asks about the conversation itself (e.g., "What did I just ask?", "انا سألتك ايه؟"), use the 'RECENT CHAT HISTORY' to answer them directly.
        3. FALLBACK: If there is no data retrieved and it's not a meta-question, politely state that you couldn't find the requested information in the company's systems. Do not invent answers.
        """),
        ("user", "{query}")
    ])
    
    try:
        res = (prompt | llm).invoke({
            "task_results": task_results if task_results else "No database records retrieved.",
            "chat_history": chat_history,
            "query": user_query
        })
        final_answer = res.content
    except Exception as e:
        print(f"[Synthesis Agent] Error: {e}")
        final_answer = "An error occurred while generating the final response."
        
    return {
        "next_agent": "END",
        "answer": final_answer
    }

def casual_chat_node(state: AgentState):
    intent = getattr(state, 'query_intent', 'casual_chat')
    print(f"\n[Guardrail] Handling query with intent: {intent} without saving to history...")
    
    llm = get_routed_llm(state)
    
    user_query = state.messages[-1].content if state.messages else ""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a polite and professional AI assistant for a company's internal RAG system (HR & IT domains).
        The user's query intent has been classified as: '{intent}'.
        
        RULES:
        - If intent is 'out_of_scope': Politely but firmly decline to answer the question. Clarify that your expertise is strictly limited to internal company matters, HR leave balances, IT tickets, and company policies. Do not answer the external question under any circumstances.
        - If intent is 'casual_chat': Respond conversationally and politely to the user's greeting or small talk. Ask how you can help them with HR or IT tasks.
        - Always respond in the same language the user used.
        - Do not attempt to search internal databases or provide factual data. Keep your response concise.
        """),
        ("user", "{query}")
    ])
    
    res = (prompt | llm).invoke({
        "query": user_query,
        "intent": intent
    })
    
    return {
        "answer": res.content,
        "next_agent": "END"
    }


async def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add Real Nodes
    workflow.add_node("Memory_Agent", memory_summarization_node) 
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Query-Planning_Agent", query_planning_node)
    workflow.add_node("Structured_Data_Agent", structured_data_node)
    
    # 2. Add Mock Nodes
    workflow.add_node("Retrieval_Agent", mock_retrieval_node)
    workflow.add_node("Verification_Agent", mock_verification_node)
    workflow.add_node("Synthesis_Agent", mock_synthesis_node)
    workflow.add_node("Casual_Chat_Agent", casual_chat_node)

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
        if state.next_agent in ["Casual_Chat_Agent", "Synthesis_Agent", "Supervisor"]:
            return state.next_agent
        return "Supervisor"

    workflow.add_conditional_edges(
        "Query-Planning_Agent", 
        planner_router,
        {
            "Casual_Chat_Agent": "Casual_Chat_Agent",
            "Synthesis_Agent": "Synthesis_Agent",
            "Supervisor": "Supervisor"
        }
    )
    
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