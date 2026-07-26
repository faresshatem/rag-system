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

    api_key = os.getenv("GROQ_API_KEY")

    # If no Groq key exists, automatically fall back to Ollama
    if not api_key:
        print("⚠️ GROQ_API_KEY not found. Falling back to Ollama.")

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )

    return ChatGroq(
        model_name="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=temperature,
    )


# Lazy initialization
api_llm = None
local_llm = None


def get_api_llm():
    global api_llm

    if api_llm is None:
        api_llm = get_llm(use_local=False)

    return api_llm


def get_local_llm():
    global local_llm

    if local_llm is None:
        local_llm = get_llm(use_local=True)

    return local_llm