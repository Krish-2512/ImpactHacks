from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.rag.retriever import retrieve_context
from backend.rag.ingestor import ingest_directory
from backend.auth.dependencies import get_current_user
from backend.config import settings
from pathlib import Path

router = APIRouter()

RAG_DATA = Path(__file__).parent.parent.parent / "rag_data"

SYSTEM_PROMPT = """You are an expert agricultural advisor for Northeast Indian farmers.
Use the provided knowledge base excerpts to answer farming questions accurately.
Focus on practical, actionable advice. If a topic is not covered in the context, say so.
Consider Northeast India's climate, soil types, and local farming practices."""


class QueryRequest(BaseModel):
    query: str
    crop: Optional[str] = None


@router.post("/query")
async def query_knowledge_base(
    payload: QueryRequest,
    _user=Depends(get_current_user),
):
    search_query = payload.query
    if payload.crop:
        search_query = f"{payload.crop} {payload.query} Northeast India"

    context_chunks = retrieve_context(search_query, top_k=5)

    if not context_chunks:
        return {
            "answer": "I don't have specific information about that in my knowledge base. "
                      "Please consult your local Krishi Vigyan Kendra (KVK) for expert advice.",
            "sources_used": 0,
        }

    context_text = "\n\n---\n\n".join(context_chunks)
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.4,
        max_tokens=1024,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Knowledge Base:\n{context_text}\n\nQuestion: {payload.query}"),
    ]
    response = await llm.ainvoke(messages)

    return {
        "answer": response.content,
        "sources_used": len(context_chunks),
        "query": payload.query,
    }


@router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks, _user=Depends(get_current_user)):
    """Admin endpoint to re-ingest all PDFs from rag_data/ folder."""
    def _run():
        total = 0
        for subdir in RAG_DATA.iterdir():
            if subdir.is_dir():
                from backend.rag.ingestor import ingest_directory as _ingest
                total += _ingest(subdir, tag=subdir.name)
        print(f"Ingestion complete: {total} chunks")

    background_tasks.add_task(_run)
    return {"message": "Ingestion started in background"}
