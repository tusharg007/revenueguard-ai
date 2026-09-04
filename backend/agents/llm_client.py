"""Configured chat-model factory."""

from backend.config import get_settings


def get_llm():
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=0.1,
            max_tokens=1024,
        )
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model=settings.LLM_MODEL,
            temperature=0.1,
            max_tokens=1024,
        )
    raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
