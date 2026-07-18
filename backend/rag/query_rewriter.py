"""
Multi-query rewriting for better RAG recall.
Generates 3 semantically diverse variants of the original query so that
different relevant chunks are surfaced from different angles.
"""
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings

_SYSTEM = (
    "You are a search query optimizer for an agricultural knowledge base. "
    "Given one search query, generate exactly 3 alternative phrasings that cover "
    "different aspects and vocabulary. Output ONLY the 3 queries, one per line, no numbering."
)


async def rewrite_query(query: str) -> list[str]:
    """Return [original] + up to 3 LLM-generated variants (4 total)."""
    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_FAST,
            temperature=0.5,
            max_tokens=150,
        )
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=f"Original query: {query}"),
        ])
        variants = [
            line.strip(" -•*\t")
            for line in response.content.strip().split("\n")
            if line.strip()
        ][:3]
        # Always keep original first, append unique variants
        all_queries = [query] + [v for v in variants if v and v.lower() != query.lower()]
        return all_queries[:4]
    except Exception as e:
        print(f"[query_rewriter] Failed (using original only): {e}")
        return [query]
