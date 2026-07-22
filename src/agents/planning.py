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
    is_dependent: str = Field(description="Set to the string 'true' if this task logically relies on the successful outcome of a previous task, or the string 'false' if it is completely independent.")

class PlannerOutput(BaseModel):
    thought_process: str = Field(description="Chain of Thought: Analyze the query and break it down into a sequence of logical steps.")
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
        3. CONTEXTUAL REWRITING: The `description` of each task must be explicit. When the user refers to "my" or "I" (e.g. "my ticket"), you MUST replace it with their actual username: '{username}'.
        4. DEPENDENCY TRACKING: For each task, evaluate if it depends on a previous task. Set `is_dependent` to the string 'true' ONLY if it needs data or a successful outcome from a previous task. Set it to the string 'false' if it can run independently (e.g., asking two unrelated questions like leave balance and CEO tickets).
        5. The plan is generated ONCE. Do not expect to replan. Provide the full plan upfront.
        
        Completed Tasks History:
        {history}
        """),
        ("user", "User Query: {query}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: PlannerOutput = chain.invoke({
            "query": user_query,
            "username": state.username or "Unknown User",
            "history": task_history if task_history else "No previous tasks."
        })
        
        updates = {}
        
        if not response.plan:
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
                    "is_dependent": str(task_def.is_dependent).strip().lower() == "true",
                    "status": "pending",
                    "result_summary": None
                })
            
            updates["tasks"] = new_tasks
            updates["current_task_id"] = None
            updates["next_agent"] = "Supervisor"
            
        return updates
        
    except Exception as e:
        print(f"Planning Agent Error: {e}")
        
        # Inject the error into the state so Synthesis Agent can inform the user
        error_task = {
            "task_id": f"task_{uuid.uuid4().hex[:6]}",
            "description": "System Error: API call failed.",
            "task_type": "vector_search",
            "target_domain": "HR",
            "is_dependent": False,
            "status": "completed",
            "result_summary": f"SYSTEM ERROR: The AI API encountered an error (e.g. Rate Limit Reached). Details: {str(e)}"
        }
        
        new_tasks = list(state.tasks)
        new_tasks.append(error_task)
        
        return {
            "tasks": new_tasks,
            "next_agent": "Synthesis_Agent", 
            "current_task_id": None, 
            "query_intent": "ready_for_synthesis"
        }