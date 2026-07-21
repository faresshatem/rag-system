import json
import os
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import text
from src.agents.state import AgentState, RetrievedChunk
from src.generation.router import get_routed_llm
from src.database.connection import engine
from redis.asyncio import Redis as AsyncRedis

class SQLQueryOutput(BaseModel):
    sql_query: str = Field(description="The valid PostgreSQL SELECT query to execute, or 'CONDITION_NOT_MET' if preconditions fail.")

DOMAIN_SCHEMAS = {
    "HR": """
    Table: users
    Columns: id (INTEGER PRIMARY KEY), full_name (VARCHAR), email (VARCHAR), department (VARCHAR), role (VARCHAR)
    
    Table: hr_leave_balances
    Columns: id (INTEGER PRIMARY KEY), user_id (INTEGER FOREIGN KEY REFERENCES users(id)), leave_type (ENUM: 'ANNUAL', 'SICK', 'MATERNITY', 'UNPAID'), available_days (INTEGER), used_days (INTEGER)
    """,
    "IT": """
    Table: users
    Columns: id (INTEGER PRIMARY KEY), full_name (VARCHAR), email (VARCHAR), department (VARCHAR), role (VARCHAR)
    
    Table: it_tickets
    Columns: id (INTEGER PRIMARY KEY), user_id (INTEGER FOREIGN KEY REFERENCES users(id)), title (VARCHAR), description (TEXT), status (ENUM: 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'), priority (ENUM: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    """
}

async def structured_data_node(state: AgentState) -> dict:
    active_task = next((t for t in state.tasks if t.task_id == state.current_task_id), None)
    if not active_task:
        return {"next_agent": "Supervisor"}
        
    target_domain = active_task.target_domain.upper()
    task_desc = active_task.description
    
    domain_schema = DOMAIN_SCHEMAS.get(target_domain)
    if not domain_schema:
        raise ValueError(f"Unknown target domain passed to Structured Agent: {target_domain}")
        
    completed_tasks = [t for t in state.tasks if t.status == 'completed']
    history_context = ""
    for idx, t in enumerate(completed_tasks):
        res_summary = str(t.result_summary)
        history_context += f"Task {idx+1}: {t.description}\nResult: {res_summary}\n\n"
        
    llm = get_routed_llm(state)
    structured_llm = llm.with_structured_output(SQLQueryOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert PostgreSQL Data Analyst for an Enterprise RAG System.
        Your sole purpose is to translate a natural language task into a highly accurate SQL SELECT query.
        
        CRITICAL CONSTRAINTS:
        1. TARGET DOMAIN: {domain}.
        2. ALLOWED SCHEMA:
        {schema}
        
        CRITICAL CONTEXT AWARENESS:
        If the Task Description refers to information from a previous task (e.g., 'the user ID found earlier', 'the status retrieved'), you MUST look at the Previous Execution History to find the exact value and use it in your SQL query.
        
        Previous Execution History:
        {history}
        
        RULES:
        - Write ONLY a valid PostgreSQL SELECT statement.
        - If the task mentions a user by name or username, ALWAYS use a JOIN with the 'users' table and filter by 'full_name' using ILIKE.
        - If the username contains underscores (e.g., 'ahmed_hassan'), replace the underscores with spaces and use wildcards (e.g., ILIKE '%ahmed hassan%') when filtering 'full_name'.
        - TRANSLATION MANDATE: If the task description or any entities/names are provided in Arabic, you MUST translate and transliterate them into their English equivalents before using them in the SQL query, as the database only stores English values. For example, convert "أحمد" to "ahmed", "حسن" to "hassan", and map Arabic terms to database enums (e.g., "مرضي" to 'SICK').
        - CRITICAL: You MUST ALWAYS include both the 'id' (from the users table) and the 'full_name' column in your SELECT statement. This ensures the system can verify the user AND passes the exact user ID to subsequent tasks in the execution history.
        - CRITICAL CONDITIONAL LOGIC: If the Task Description contains a condition (e.g., "If the ticket is 'RESOLVED'...") AND you see from the Previous Execution History that this condition is FALSE, you MUST NOT generate a valid SQL query. Instead, output EXACTLY the phrase: "CONDITION_NOT_MET".
        """),
        ("user", "Task Description: {task}\n\nGenerate the exact SQL query.")
    ])
    
    try:
        response = await (prompt | structured_llm).ainvoke({
            "domain": target_domain,
            "schema": domain_schema,
            "task": task_desc,
            "history": history_context if history_context else "No previous tasks."
        })
        sql_query = response.sql_query
        
        if sql_query.strip() == "CONDITION_NOT_MET":
            print(f"\n[Structured Agent] Task Skipped: Condition not met based on history.\n")
            result_text = "Task Skipped: The condition specified in the task description was not met based on previous results."
            summary = result_text
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis_client = AsyncRedis.from_url(redis_url)
            cache_key = f"sql_cache_v1.3:{sql_query}"
            
            cached_result = await redis_client.get(cache_key)
            
            if cached_result:
                print(f"\n[Structured Agent] Cache hit for SQL: {sql_query}\n")
                data = json.loads(cached_result)
                result_text = data["result_text"]
                summary = data["summary"]
            else:
                print(f"\n[Structured Agent] Executing SQL: {sql_query}\n")
                
                async with engine.begin() as conn:
                    result = await conn.execute(text(sql_query))
                    rows = result.fetchall()
                    keys = result.keys()
                    
                    formatted_data = [dict(zip(keys, row)) for row in rows]
                    
                if not formatted_data:
                    result_text = "Query executed successfully, but no matching records were found in the database."
                    summary = "No records found."
                else:
                    result_text = json.dumps(formatted_data, indent=2, default=str)
                    raw_json_str = json.dumps(formatted_data, default=str)
                    
                    # Smart Summarization Logic 
                    if len(raw_json_str) > 400:
                        print(f"   -> [Smart Summarization] Data too large ({len(raw_json_str)} chars). Extracting key info...")
                        
                        summary_prompt = ChatPromptTemplate.from_messages([
                            ("system", "You are an expert data extractor. Extract the exact answer for the given task from the provided JSON data. Be extremely concise, factual, and keep your response under 300 characters. Do not use conversational filler."),
                            ("user", "Task: {task}\nJSON Data: {data}")
                        ])
                        
                        summary_chain = summary_prompt | llm 
                        summary_response = await summary_chain.ainvoke({
                            "task": task_desc,
                            "data": raw_json_str
                        })
                        
                        extracted_info = summary_response.content
                        summary = f"Retrieved {len(formatted_data)} record(s). Extracted info: {extracted_info}"
                    else:
                        summary = f"Retrieved {len(formatted_data)} record(s): {raw_json_str}"
                    
                data_to_cache = {
                    "result_text": result_text,
                    "summary": summary
                }
                await redis_client.set(cache_key, json.dumps(data_to_cache), ex=3600)
            
    except Exception as e:
        print(f"[Structured Agent] Error: {e}")
        result_text = f"Database query failed due to an error: {str(e)}"
        summary = "Failed to execute database lookup."

    chunk = RetrievedChunk(
        chunk_id=f"{active_task.task_id}_db",
        file_name=f"{target_domain}_SQL_Database",
        text=result_text,
        page=None
    )
    
    updated_tasks = list(state.tasks)
    for t in updated_tasks:
        if t.task_id == state.current_task_id:
            t.status = "completed"
            t.result_summary = summary
            
    updated_context = list(state.retrieved_context) + [chunk]
    
    return {
        "tasks": updated_tasks,
        "retrieved_context": updated_context,
        "next_agent": "Verification_Agent"
    }