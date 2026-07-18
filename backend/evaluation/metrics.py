"""
RAGAS-style evaluation metrics for Agrow RAG pipeline.

faithfulness()       — LLM-as-judge: fraction of report claims supported by RAG sources
answer_relevance()   — embedding cosine similarity between final_report and rag_query
context_precision()  — fraction of RAG chunks that are relevant to the rag_query (LLM-as-judge)
"""
import json
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _llm_json(prompt: str, system: str, max_tokens: int = 400) -> dict[str, Any]:
    """Helper: call GROQ_MODEL_FAST and parse JSON response."""
    from groq import AsyncGroq
    from backend.config import settings

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    resp = await client.chat.completions.create(
        model=settings.GROQ_MODEL_FAST,
        temperature=0.0,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("Metrics LLM returned non-JSON: %s", raw[:200])
        return {}


async def faithfulness(
    final_report: str,
    rag_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Returns {"faithfulness": float, "unsupported_claims": list[str]}
    Faithfulness = fraction of claims in final_report supported by rag_sources.
    """
    if not final_report or not rag_sources:
        return {"faithfulness": 0.0, "unsupported_claims": [], "error": "missing inputs"}

    # Build a compact source excerpt (first 300 chars per source, up to 5 sources)
    source_text = "\n---\n".join(
        s.get("text", "")[:300] for s in rag_sources[:5]
    )
    report_excerpt = final_report[:800]

    system = (
        "You are an agricultural AI auditor. Evaluate only what the sources explicitly support. "
        "Return valid JSON, no markdown."
    )
    prompt = (
        f"Source chunks:\n{source_text}\n\n"
        f"Report excerpt:\n{report_excerpt}\n\n"
        "Rate what fraction of claims in the report are supported by the sources (0.0–1.0). "
        'Return JSON: {"faithfulness": 0.85, "unsupported_claims": ["claim1", "claim2"]}'
    )

    result = await _llm_json(prompt, system, max_tokens=300)
    return {
        "faithfulness": float(result.get("faithfulness", 0.0)),
        "unsupported_claims": result.get("unsupported_claims", []),
    }


async def answer_relevance(
    final_report: str,
    rag_query: str,
) -> dict[str, Any]:
    """
    Returns {"answer_relevance": float}
    Cosine similarity between embed(final_report[:512]) and embed(rag_query).
    """
    if not final_report or not rag_query:
        return {"answer_relevance": 0.0, "error": "missing inputs"}

    try:
        from fastembed import TextEmbedding
        import asyncio

        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

        def _embed(texts: list[str]) -> list[list[float]]:
            return [list(v) for v in model.embed(texts)]

        report_trunc = final_report[:512]
        vecs = await asyncio.to_thread(_embed, [report_trunc, rag_query])
        sim = _cosine(vecs[0], vecs[1])
        return {"answer_relevance": round(sim, 4)}

    except Exception as e:
        logger.warning("answer_relevance embedding failed: %s", e)
        return {"answer_relevance": 0.0, "error": str(e)}


async def context_precision(
    rag_query: str,
    rag_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Returns {"context_precision": float, "relevant_count": int, "total_count": int}
    Fraction of retrieved RAG chunks that are relevant to the query (LLM-as-judge).
    """
    if not rag_query or not rag_sources:
        return {"context_precision": 0.0, "relevant_count": 0, "total_count": 0}

    chunks_text = "\n---\n".join(
        f"[{i+1}] {s.get('text', '')[:200]}" for i, s in enumerate(rag_sources[:8])
    )
    n = min(len(rag_sources), 8)

    system = (
        "You are an agricultural information retrieval evaluator. "
        "Return valid JSON, no markdown."
    )
    prompt = (
        f"Query: {rag_query}\n\n"
        f"Retrieved chunks:\n{chunks_text}\n\n"
        f"For each chunk [1]–[{n}], decide if it is relevant (true/false) to the query. "
        f'Return JSON: {{"relevant_indices": [1, 3, 5], "context_precision": 0.6}}'
    )

    result = await _llm_json(prompt, system, max_tokens=200)
    relevant = result.get("relevant_indices", [])
    precision = len(relevant) / n if n > 0 else 0.0
    return {
        "context_precision": round(result.get("context_precision", precision), 4),
        "relevant_count": len(relevant),
        "total_count": n,
        "relevant_indices": relevant,
    }
