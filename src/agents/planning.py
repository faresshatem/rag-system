from typing import List
from pydantic import BaseModel, Field
from src.agents.state import AgentState
from src.generation.router import get_routed_llm
from langchain_core.prompts import ChatPromptTemplate

class PlanOutput(BaseModel):
    tasks: List[str] = Field(
        description="A list of distinct search tasks broken down from the user query. Each task MUST explicitly mention the target domain (e.g., HR or IT)."
    )

def query_planning_node(state: AgentState) -> dict:
    llm = get_routed_llm(state)
    structured_llm = llm.with_structured_output(PlanOutput)
    user_query = state.messages[-1].content if state.messages else ""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a planning assistant for an Enterprise RAG system. 
        Analyze the user's query and break it down into explicit search tasks.
        Available domains are: HR, IT."""),
        ("user", "{query}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: PlanOutput = chain.invoke({"query": user_query})
        plan_list = response.tasks
        
    except Exception as e:
        print(f"Planning Agent Error: {e}")
        plan_list = [f"Search knowledge base for: {user_query}"]
        
    return {
        "plan": plan_list,
        "next_agent": "Supervisor" 
    }