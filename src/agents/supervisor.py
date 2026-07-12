import os
from src.agents.state import AgentState

def supervisor_node(state: AgentState) -> dict:
    
    budget = int(os.getenv("MAX_STEPS_BUDGET", 7))
    current_step = state.step_count
    current_plan = state.plan or [] 
    
    if current_step >= budget:
        return {
            "next_agent": "Synthesis_Agent",
            "step_count": current_step + 1
        }
        
    if state.plan is None:
        return {
            "next_agent": "Query-Planning_Agent",
            "step_count": current_step + 1
        }
        
    if state.is_context_valid is False:
        return {
            "next_agent": "Retrieval_Agent",
            "step_count": current_step + 1
        }
    elif state.is_context_valid is True and len(current_plan) > 0:
        current_plan = current_plan[1:]

    if len(current_plan) == 0:
        return {
            "next_agent": "Synthesis_Agent",
            "step_count": current_step + 1,
            "plan": current_plan
        }
        
    current_task = current_plan[0] 
    
    target_domain = "HR" if "HR" in current_task.upper() else "IT" if "IT" in current_task.upper() else None
    
    if target_domain and target_domain not in state.allowed_domains:
        return {
            "next_agent": "Synthesis_Agent",
            "step_count": current_step + 1,
            "verification_feedback": f"Access Denied: You do not have permission to access the {target_domain} domain."
        }
        
    return {
        "next_agent": "Retrieval_Agent",
        "target_domain": target_domain,
        "step_count": current_step + 1,
        "plan": current_plan,
        "is_context_valid": None 
    }