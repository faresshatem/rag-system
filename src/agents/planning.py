import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState
from src.generation.router import get_routed_llm

class TaskDefinition(BaseModel):
    description: str = Field(description="Explicit, self-contained description of the search or lookup task.")
    task_type: str = Field(description="Must be either 'vector_search' or 'structured_db_lookup'")
    target_domain: str = Field(description="Target domain, e.g., 'HR' or 'IT'")

class PlannerOutput(BaseModel):
    thought_process: str = Field(description="Chain of Thought: Analyze the query and break it down into a sequence of logical steps.")
    query_intent: str = Field(description="Must be 'casual_chat', 'information_retrieval', or 'ready_for_synthesis'")
    plan: List[TaskDefinition] = Field(default_factory=list, description="An ordered list of ALL tasks required to answer the user query completely.")

def query_planning_node(state: AgentState) -> dict:
    llm = get_routed_llm(state)
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    user_query = state.messages[0].content if state.messages else ""
    
    # Dynamic Replanning
    completed_tasks = [t for t in state.tasks if t.status == 'completed']
    task_history = ""
    for idx, t in enumerate(completed_tasks):
        #Context Overflow      
        res_summary = str(t.result_summary)[:300] if t.result_summary else "None"
        task_history += f"Task {idx+1}: {t.description}\nResult: {res_summary}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Master Planner for an Enterprise RAG system.
        Your job is to analyze complex user queries and create a COMPLETE execution plan.
        Available domains: HR, IT.
        Task Types: 'vector_search' (for policies/documents) or 'structured_db_lookup' (for databases).
        
        RULES FOR PLAN CREATION:
        1. Break the user's query into a logical sequence of interdependent tasks.
        2. Generate ALL necessary tasks AT ONCE in the correct execution order.
        3. CONTEXTUAL REWRITING: The `description` of each task must be explicit.
        4. DYNAMIC REPLANNING: If you see previous 'Completed Tasks' that failed or changed the context, adjust your new plan accordingly.
        5. If all logical tasks are done based on the History, set intent to 'ready_for_synthesis' and leave the plan empty.
        INTENT CLASSIFICATION AND TASK RULES:
        1. "information_retrieval": Use this ONLY if the user is asking for specific internal company data, IT tickets, HR leave balances, or company policies.
        2. "casual_chat": Use this for greetings (e.g., "hi", "how are you"), small talk, AND general world knowledge questions (e.g., "tell me about AI", "what is Python?"). 

        CRITICAL CONSTRAINT for 'casual_chat':
        If the query intent is "casual_chat", you MUST return an EMPTY tasks list ([]). DO NOT create any tasks for general knowledge or casual conversations.
        Completed Tasks History:
        {history}
        """),
        ("user", "User Query: {query}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: PlannerOutput = chain.invoke({
            "query": user_query,
            "history": task_history if task_history else "No previous tasks."
        })
        
        updates = {"query_intent": response.query_intent}
        
        if response.query_intent in ["casual_chat", "ready_for_synthesis"] or not response.plan:
            updates["next_agent"] = "Synthesis_Agent"
            updates["current_task_id"] = None
            updates["query_intent"] = "ready_for_synthesis"
        else:
            # the pending tasks
            new_tasks = list(completed_tasks)
            for task_def in response.plan:
                new_tasks.append({
                    "task_id": f"task_{uuid.uuid4().hex[:6]}",
                    "description": task_def.description,
                    "task_type": task_def.task_type,
                    "target_domain": task_def.target_domain,
                    "status": "pending",
                    "result_summary": None
                })
            
            updates["tasks"] = new_tasks
            updates["current_task_id"] = None
            updates["next_agent"] = "Supervisor"
            
        return updates
        
    except Exception as e:
        print(f"Planning Agent Error: {e}")
        return {"next_agent": "Synthesis_Agent", "current_task_id": None, "query_intent": "ready_for_synthesis"}