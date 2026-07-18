import os
from src.agents.state import AgentState

def supervisor_node(state: AgentState) -> dict:
    print("\n--- Supervisor ---")
    
    # 1. Dynamic Budget Calculation
    base_steps = 3  # (1 Planner + 1 Synthesis + 1 Buffer)
    if not state.tasks:
        budget = int(os.getenv("MAX_STEPS_BUDGET", 12))
    else:
        budget = base_steps + (len(state.tasks) * 4)
        
    current_step = state.step_count
    
    # 2. Check Budget (Prevent Infinite Loops)
    if current_step >= budget:
        print(f"Supervisor: Dynamic Budget exceeded ({current_step}/{budget} steps). Routing to Synthesis.")
        return {"next_agent": "Synthesis_Agent", "step_count": current_step + 1}
        
    # Honor explicit requests to Synthesis
    if state.next_agent == "Synthesis_Agent":
        print("Supervisor: Honoring explicit route to Synthesis.")
        return {"next_agent": "Synthesis_Agent", "step_count": current_step + 1}
        
    # 3. Check for Final Intent from Planner
    if state.query_intent in ["casual_chat", "ready_for_synthesis"]:
        print(f"Supervisor: Intent is {state.query_intent}. Routing to Synthesis.")
        return {"next_agent": "Synthesis_Agent", "step_count": current_step + 1}
        
    # 4. Handle Verification Failures (Domino Effect & Dynamic Replanning)
    active_task = None
    if state.current_task_id:
        active_task = next((t for t in state.tasks if t.task_id == state.current_task_id), None)
        
    if state.is_context_valid is False and active_task:
        # solve (Abort Plan)
        if "No records found" in str(active_task.result_summary):
            print(f"Supervisor: Domino Effect! Task [{active_task.task_id}] returned empty. Aborting the rest of the plan.")
            return {"next_agent": "Synthesis_Agent", "current_task_id": None, "step_count": current_step + 1}
        
        # solve (Dynamic Replanning)
        else:
            print(f"Supervisor: Task [{active_task.task_id}] failed validation. Routing back to Planner for Dynamic Replanning.")
            return {"next_agent": "Query-Planning_Agent", "current_task_id": None, "step_count": current_step + 1}

    # 5. Plan Execution Logic
    if not state.tasks:
        print("Supervisor: No active plan. Routing to Planner.")
        return {"next_agent": "Query-Planning_Agent", "step_count": current_step + 1}
        
    pending_tasks = [t for t in state.tasks if t.status == "pending"]
    
    if not pending_tasks:
        print("Supervisor: All planned tasks completed successfully! Routing to Synthesis.")
        return {
            "next_agent": "Synthesis_Agent", 
            "current_task_id": None,
            "step_count": current_step + 1
        }
        
    next_task = pending_tasks[0]
    
    # 6. Strict RBAC (Role-Based Access Control) Check 
    target_domain = next_task.target_domain
    if target_domain and target_domain not in state.allowed_domains:
        print(f"Supervisor: Access Denied for domain {target_domain}. Skipping task [{next_task.task_id}].")
        
        updated_tasks = list(state.tasks)
        for t in updated_tasks:
            if t.task_id == next_task.task_id:
                t.status = "completed"
                t.result_summary = f"ACCESS DENIED: User does not have permission to access the {target_domain} domain."
        
        return {
            "tasks": updated_tasks,
            "next_agent": "Supervisor",
            "current_task_id": None,
            "step_count": current_step + 1
        }
        
    # 7. Dynamic Routing to Specialists based on task_type
    next_node = "Retrieval_Agent" if next_task.task_type == "vector_search" else "Structured_Data_Agent"
    print(f"Supervisor: Routing to {next_node} for Task [{next_task.task_id}] (Domain: {target_domain}).")
    
    return {
        "current_task_id": next_task.task_id,
        "next_agent": next_node,
        "target_domain": target_domain,
        "step_count": current_step + 1,
        "is_context_valid": None 
    }