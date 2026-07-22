from src.agents.state import AgentState 
from src.generation.generator import get_llm

def is_domain_sensitive(domain: str) -> bool:
    SENSITIVE_DOMAINS = ["HR"]
    
    if not domain:
        return False
        
    return domain.upper() in SENSITIVE_DOMAINS

def get_routed_llm(state: AgentState):
    if state.next_agent in ["Supervisor", "Query-Planning_Agent" , "Casual_Chat_Agent"]:
        return get_llm(use_local=False, temperature=0.0)
        
    if state.target_domain:
        use_local = is_domain_sensitive(state.target_domain)
        return get_llm(use_local=use_local, temperature=0.0)
        
    return get_llm(use_local=False, temperature=0.0)