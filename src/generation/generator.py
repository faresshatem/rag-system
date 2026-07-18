import os
from dotenv import load_dotenv, find_dotenv
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

load_dotenv(find_dotenv())

def get_llm(use_local: bool = False, temperature: float = 0.0):
    if use_local:
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )
    else:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in the environment variables.")
            
        return ChatGroq(
            model_name="llama-3.3-70b-versatile", 
            groq_api_key=api_key,
            temperature=temperature,
        )

api_llm = get_llm(use_local=False)  
local_llm = get_llm(use_local=True) 
