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
    query_intent: str = Field(description="Must be 'casual_chat', 'information_retrieval', 'ready_for_synthesis', or 'out_of_scope'")
    plan: List[TaskDefinition] = Field(default_factory=list, description="An ordered list of ALL tasks required to answer the user query completely.")

def query_planning_node(state: AgentState) -> dict:
    llm = get_routed_llm(state)
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    user_query = state.messages[-1].content if state.messages else ""
    
    last_assistant_msg = "No previous response."
    if len(state.messages) > 1:
        for msg in reversed(state.messages[:-1]):
            role = getattr(msg, 'role', getattr(msg, 'type', ''))
            if role in ['assistant', 'ai']:
                last_assistant_msg = msg.content
                break

        if last_assistant_msg == "No previous response.":
            last_assistant_msg = state.messages[-2].content

    chat_summary = getattr(state, 'conversation_summary', "")
    
    completed_tasks = [t for t in state.tasks if t.status == 'completed']
    task_history = ""
    for idx, t in enumerate(completed_tasks):
        res_summary = str(t.result_summary)[:300] if t.result_summary else "None"
        task_history += f"Task {idx+1}: {t.description}\nResult: {res_summary}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Master Planner for an Enterprise RAG system.
        Your job is to analyze complex user queries and create a COMPLETE execution plan.
        Available domains: HR, IT.
        Task Types: 'vector_search' (for policies/documents) or 'structured_db_lookup' (for databases).
        
        CONVERSATION SUMMARY (Older Memory):
        {summary}
        
        IMMEDIATE PREVIOUS RESPONSE (Crucial for context like "them", "it"):
        {last_response}
        
        RULES FOR PLAN CREATION:
        1. Break the user's query into a logical sequence of interdependent tasks.
        2. Generate ALL necessary tasks AT ONCE in the correct execution order.
        3. CONTEXTUAL REWRITING & FILTERING (CRITICAL): Use 'IMMEDIATE PREVIOUS RESPONSE' and 'Completed Tasks History' to understand what pronouns like 'them', 'these', or 'it' refer to. If the user asks to filter previous results (e.g., "هات اللي اسمهم سلمي منهم"), your new task description MUST combine the old context with the new filter (e.g., "Search for employee named Salma specifically in HR annual leave balances"). DO NOT generate a vague task.
        4. DEPENDENCY TRACKING: Set `is_dependent` to 'true' ONLY if it needs data or a successful outcome from a previous task.
        5. CANCELLATIONS (CRITICAL): If the user cancels a request mid-sentence, strictly ignore it.
        6. IDENTITY SECURITY: Map first-person pronouns ("I", "my", "بتاعتي") strictly to the authenticated username: '{username}'.

        INTENT CLASSIFICATION AND TASK RULES:
        1. "information_retrieval": Use for queries related to company domains (IT, HR, policies, employees).
        2. "ready_for_synthesis": Use this if the user asks a meta-question about the conversation history itself (e.g., "what did I just ask?", "انا سالت ايه", "الرسالة اللي فاتت").
        3. "out_of_scope": Use for general knowledge/external queries. EXCEPTION: Do NOT use this for questions about the chat history.
        4. "casual_chat": Use ONLY for pure greetings.

        CRITICAL CONSTRAINT: If intent is "out_of_scope" or "casual_chat", return an EMPTY tasks list ([]).
        
        Completed Tasks History:
        {history}
        """),
        ("user", "User Query: {query}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: PlannerOutput = chain.invoke({
            "query": user_query,
            "summary": chat_summary if chat_summary else "No previous conversation context.",
            "last_response": last_assistant_msg,
            "username": state.username or "Unknown User",
            "history": task_history if task_history else "No previous tasks."
        })
        
        intent = str(response.query_intent).strip().lower().replace(" ", "_")
        updates = {"query_intent": intent}
        
        if intent in ["casual_chat", "out_of_scope"]:
            updates["next_agent"] = "Casual_Chat_Agent"
            updates["current_task_id"] = None
        elif intent == "ready_for_synthesis" or not response.plan:
            updates["next_agent"] = "Synthesis_Agent"
            updates["current_task_id"] = None
        else:
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
        return {
            "next_agent": "Synthesis_Agent", 
            "current_task_id": None, 
            "query_intent": "ready_for_synthesis"
        }