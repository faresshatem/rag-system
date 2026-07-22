import os
from typing import List
from src.agents.state import AgentState, Message
from src.generation.router import get_routed_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

def summarize_history(llm, history: List[Message]) -> List[Message]:
    """Summarizes a list of casual chat messages to save context space."""
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert AI summarizer. Summarize the following conversation concisely. Focus on the main topics discussed, user preferences, and any important facts. Return only the summary text."),
        ("user", "{conversation}")
    ])
    
    res = (prompt | llm).invoke({"conversation": history_text})
    
    return [
        Message(role="system", content=f"Summary of previous conversation:\n{res.content}")
    ]

def casual_chat_node(state: AgentState):
    print("\n[Casual Chat] Handling conversational query...")
    llm = get_routed_llm(state)
    
    # Get the latest user query
    user_query = state.messages[-1].content if state.messages else ""
    
    # Extract independent history
    chat_history = list(state.casual_chat_history)
    
    # Format history for the agent input
    formatted_messages = []
    for msg in chat_history:
        formatted_messages.append((msg.role, msg.content))
        
    # Append the current query
    formatted_messages.append(("user", user_query))
    
    # Initialize tools
    tools = []
    if os.getenv("TAVILY_API_KEY"):
        tavily_tool = TavilySearch(max_results=3)
        tools.append(tavily_tool)
    
    system_prompt = (
        "You are a helpful and polite AI assistant. Respond conversationally to the user's greeting or general question. "
        "Do not attempt to search internal databases. "
        "If the user asks a question and you do not know the answer, lack information, the information is outdated, or the user asks to search the internet, "
        "you MUST use the tavily_search_results_json tool to search the internet and provide an up-to-date answer.\n\n"
        "IMPORTANT ABOUT HISTORY: You are provided with the conversation history or its summary. "
        "ONLY use this history if the user's current message is a follow-up or refers back to it (e.g., using pronouns or continuing the topic). "
        "If the user asks a completely new question or just says a general greeting like 'Hello', treat it as an independent question and DO NOT unnecessarily bring up the previous topics."
    )
    
    if tools:
        # Create a React agent with the tools
        agent_executor = create_react_agent(llm, tools, prompt=system_prompt)
        # Invoke the agent with the history + current user message
        result = agent_executor.invoke({"messages": formatted_messages})
        final_answer = result["messages"][-1].content
    else:
        # Fallback if no Tavily API Key
        msgs = [("system", system_prompt)] + formatted_messages
        prompt = ChatPromptTemplate.from_messages(msgs)
        res = (prompt | llm).invoke({})
        final_answer = res.content
        
    # Update independent casual chat history
    chat_history.append(Message(role="user", content=user_query))
    chat_history.append(Message(role="assistant", content=final_answer))
    
    # Summarize if it exceeds 6 messages (3 interactions + possible system summary)
    if len(chat_history) > 6:
        print(f"\n[Casual Chat] History limit exceeded ({len(chat_history)} messages). Summarizing...")
        chat_history = summarize_history(llm, chat_history)
    
    # Return answer and updated casual chat history
    return {
        "answer": final_answer,
        "casual_chat_history": chat_history,
        "next_agent": "END"
    }
