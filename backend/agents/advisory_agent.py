import asyncio
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.rag.retriever import retrieve_context_with_sources
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural advisor for Northeast Indian farmers.
Use the provided knowledge base excerpts to give accurate, practical cultivation advice.
Focus on: pest management, soil care, watering schedules, and harvest timing.
If the context doesn't cover the question, acknowledge it honestly and use general expertise."""


def _build_rag_query(state: AgentState) -> str:
    crops = state.get("farm_state", {}).get("primary_crops", ["tomato", "brinjal"])
    condition = state["weather_forecast"].get("Condition", "")
    humidity = state["weather_forecast"].get("Humidity", 60)
    try:
        extra = "fungal disease" if float(humidity) > 80 else "pest management"
    except (TypeError, ValueError):
        extra = "pest management"
    return f"cultivation guide {' '.join(crops)} {condition} {extra} Northeast India organic farming"


async def run(state: AgentState) -> AgentState:
    t0 = time.perf_counter()
    query = _build_rag_query(state)

    # retrieve_context_with_sources is sync — wrap in thread to avoid blocking event loop
    try:
        results = await asyncio.to_thread(retrieve_context_with_sources, query, 5)
        context_chunks = [r["text"] for r in results]
        rag_sources = results
    except Exception as e:
        print(f"[advisory_agent] RAG retrieval failed: {e}")
        context_chunks, rag_sources = [], []

    def _f(v, fallback="N/A"):
        try: return f"{float(v):.1f}"
        except (TypeError, ValueError): return str(fallback)

    crops = state.get("farm_state", {}).get("primary_crops", ["tomato", "brinjal"])
    w = state["weather_forecast"]
    weather_summary = (
        f"{w.get('Condition', 'N/A')} weather, "
        f"{_f(w.get('Temperature'))}°C, "
        f"{_f(w.get('Humidity'))}% humidity"
    )

    # Include market context — advisory agent now knows SELL/HOLD decisions
    market_decisions = state.get("sell_hold_decisions", {})
    market_context = ""
    if market_decisions:
        lines = [f"{crop}: {decision}" for crop, decision in market_decisions.items()]
        market_context = f"\nMarket decisions (for harvest timing context): {', '.join(lines)}"

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.4,
        max_tokens=900,
    )

    if context_chunks:
        context_text = "\n\n---\n\n".join(context_chunks)
        kb_section = f"Knowledge Base:\n{context_text}\n\n"
    else:
        kb_section = "Note: No specific knowledge base entries found. Use general agricultural expertise.\n\n"

    user_msg = f"""{kb_section}Current farm conditions:
- Crops: {', '.join(crops)}
- Weather: {weather_summary}{market_context}

Provide:
1. Today's top cultivation advice for each listed crop
2. Pest or disease warnings given the current weather conditions
3. Specific treatment or preventive actions recommended
4. Harvest timing advice considering current market decisions"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content

    pest_warnings = [
        line.strip("- •*").strip()
        for line in text.split("\n")
        if any(w in line.lower() for w in ["pest", "disease", "blight", "mite", "fungal", "warning", "risk", "infection"])
        and len(line.strip()) > 15
    ]

    confidence = 0.85 if context_chunks else 0.60
    elapsed = (time.perf_counter() - t0) * 1000
    timings = {**state.get("agent_timings", {}), "advisory": round(elapsed, 1)}

    return {
        **state,
        "rag_query": query,
        "rag_sources": rag_sources,
        "crop_advisory": text,
        "pest_warnings": pest_warnings[:4],
        "advisory_confidence": confidence,
        "agent_timings": timings,
    }
