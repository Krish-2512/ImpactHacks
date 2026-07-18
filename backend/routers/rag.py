from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.rag.retriever import retrieve_context_multi_query
from backend.rag.ingestor import ingest_directory
from backend.auth.dependencies import get_current_user
from backend.config import settings
from pathlib import Path

router = APIRouter()

RAG_DATA = Path(__file__).parent.parent.parent / "rag_data"

SYSTEM_PROMPT = """You are an expert agricultural advisor for Northeast Indian farmers.
Use the provided knowledge base excerpts to answer farming questions accurately.
Focus on practical, actionable advice. Cite your sources when possible.
If a topic is not covered in the context, say so honestly.
Consider Northeast India's climate, soil types, and local farming practices."""


class QueryRequest(BaseModel):
    query: str
    crop: Optional[str] = None


@router.post("/query")
async def query_knowledge_base(
    payload: QueryRequest,
    _user=Depends(get_current_user),
):
    search_query = f"{payload.crop} {payload.query} Northeast India" if payload.crop else payload.query

    # Multi-query retrieval with MMR — fully async, no event loop blocking
    results = await retrieve_context_multi_query(search_query, top_k=5)

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.4,
        max_tokens=1024,
    )

    if not results:
        # No RAG hits — answer from LLM general knowledge with honest disclaimer
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"No specific knowledge base entries were found for this query.\n"
                f"Question: {payload.query}\n\n"
                "Answer using your general agricultural expertise for Northeast India. "
                "Begin your answer with a brief note that this is from general expertise, not a local knowledge base entry."
            )),
        ]
        response = await llm.ainvoke(messages)
        return {
            "answer": response.content,
            "sources_used": 0,
            "sources": [],
            "query": payload.query,
            "note": "answered from general LLM knowledge — no matching knowledge base entries",
        }

    context_text = "\n\n---\n\n".join(r["text"] for r in results)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Knowledge Base:\n{context_text}\n\nQuestion: {payload.query}"),
    ]
    response = await llm.ainvoke(messages)

    citations = [
        {
            "source": r["source"],
            "tag":    r["tag"],
            "score":  r["score"],
            "excerpt": r["text"][:200] + "...",
        }
        for r in results
    ]

    return {
        "answer": response.content,
        "sources_used": len(results),
        "sources": citations,
        "query": payload.query,
    }


@router.post("/ingest")
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    _user=Depends(get_current_user),
):
    """Admin endpoint — re-ingests all PDFs/TXTs from rag_data/ in background."""
    def _run():
        total = 0
        for subdir in sorted(RAG_DATA.iterdir()):
            if subdir.is_dir():
                n = ingest_directory(subdir, tag=subdir.name)
                total += n
                print(f"Ingested {n} chunks from {subdir.name}/")
        print(f"Total ingested: {total} chunks")

    background_tasks.add_task(_run)
    return {"message": "Ingestion started in background. Check server logs for progress."}
