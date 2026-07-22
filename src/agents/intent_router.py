from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentState
from src.generation.router import get_routed_llm

class IntentOutput(BaseModel):
    query_intent: str = Field(description="Must be either 'casual_chat' or 'information_retrieval'")

def intent_router_node(state: AgentState) -> dict:
    print("\n--- Intent Router ---")
    user_query = state.messages[-1].content if state.messages else ""
    
    if not user_query:
        return {"next_agent": "END"}
        
    llm = get_routed_llm(state)
    structured_llm = llm.with_structured_output(IntentOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the master routing gateway for an enterprise AI system. 
        Your sole responsibility is to classify the user's intent to route them to the appropriate specialized agent.
        
        System Capabilities:
        1. SQL Database (Structured Data): Contains exact tabular data. 
           - HR Schema: `users` (id, full_name, email, department, role), `hr_leave_balances` (id, user_id, leave_type, available_days, used_days).
           - IT Schema: `users` (id, full_name, email, department, role), `it_tickets` (id, user_id, title, description, status, priority).
           - If the user asks for data that doesn't fit these tables (e.g., salaries, marketing campaigns, finance records), it is NOT in the database.
        2. Vector Database (Unstructured Data): Handles unstructured text like HR policies, IT guidelines, and company documents.
           - If the user asks for documents outside HR or IT, it is NOT in the vector database.
        
        CRITICAL ROUTING RULES:
        1. "information_retrieval": Use this ONLY if the user is asking about HR or IT related data, policies, tickets, or documents. This intent is used to route to BOTH the Vector Database (Retrieval Agent) AND the SQL Database (Structured Agent).
           - Examples: "What is my leave balance?" (SQL), "Show me my open IT tickets" (SQL), "What is the policy for sick leave?" (Vector), "Find the IT onboarding document" (Vector).
        2. "casual_chat": Use this for everything else.
           - Examples: Greetings ("Hello", "How are you?"), general knowledge ("What is the capital of France?").
           - CRITICAL: If the user asks for documents, files, or information related to ANY domain OTHER THAN HR or IT (e.g., Finance, Marketing, Sales, Engineering), you MUST route them to "casual_chat". We do not have retrieval capabilities for these domains yet.
           
        Analyze the user's query and output the exact query_intent.
        """),
        ("user", "User Query: {query}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: IntentOutput = chain.invoke({"query": user_query})
        intent = str(response.query_intent).strip().lower()
        
        print(f"Intent Router: Classified intent as '{intent}'")
        
        if intent == "casual_chat":
            return {"query_intent": "casual_chat", "next_agent": "Casual_Chat_Agent"}
        else:
            return {"query_intent": "information_retrieval", "next_agent": "Supervisor"}
            
    except Exception as e:
        print(f"Intent Router: Failed to classify intent ({e}). Defaulting to Supervisor.")
        return {"query_intent": "information_retrieval", "next_agent": "Supervisor"}
