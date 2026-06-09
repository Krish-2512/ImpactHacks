import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.rag.retriever import retrieve_context
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural advisor for Northeast Indian farmers.
Use the provided knowledge base excerpts to give accurate, practical cultivation advice.
Focus on: pest management, soil care, watering schedules, and harvest timing.
If the context doesn't cover the question, acknowledge it honestly."""


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
    query = _build_rag_query(state)
    # retrieve_context is sync (CPU + network) — run in thread to avoid blocking event loop
    context_chunks = await asyncio.to_thread(retrieve_context, query, 5)

    crops = state.get("farm_state", {}).get("primary_crops", ["tomato", "brinjal"])
    weather_summary = (
        f"{state['weather_forecast'].get('Condition', 'N/A')} weather, "
        f"{state['weather_forecast'].get('Temperature', 'N/A'):.1f}°C, "
        f"{state['weather_forecast'].get('Humidity', 'N/A'):.1f}% humidity"
    )

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
        kb_section = "Note: No specific knowledge base entries found. Use general expertise.\n\n"

    user_msg = f"""{kb_section}Current farm conditions:
- Crops: {', '.join(crops)}
- Weather: {weather_summary}

Provide:
1. Today's top cultivation advice for the listed crops
2. Pest or disease warnings given the current weather
3. Any treatment or preventive actions recommended"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content

    pest_warnings = [
        line.strip("- •*").strip()
        for line in text.split("\n")
        if any(w in line.lower() for w in ["pest", "disease", "blight", "mite", "fungal", "warning", "risk"])
        and len(line.strip()) > 15
    ]

    return {
        **state,
        "rag_query": query,
        "crop_advisory": text,
        "pest_warnings": pest_warnings[:4],
    }
