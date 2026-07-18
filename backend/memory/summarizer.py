from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings


async def summarize_memories(memories: list) -> str:
    """
    Turn the last N memory entries into a short context paragraph.
    Returns "" if no memories exist (first-time farmer).
    """
    if not memories:
        return ""

    lines = []
    for m in memories[:15]:
        text = m.get("memory_text") or m.get("recommendation_summary") or ""
        if text:
            lines.append(f"[{m.get('date', '?')}] {text}")

    if not lines:
        return ""

    combined = "\n".join(lines)

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.1,
        max_tokens=300,
    )

    response = await llm.ainvoke([
        SystemMessage(content=(
            "You summarize a farmer's recent activity history in 3-4 concise sentences. "
            "Include: recurring problems, what worked, recent weather/market patterns. "
            "This summary will be injected as context for today's AI agents."
        )),
        HumanMessage(content=f"Farmer's recent history (newest first):\n{combined}\n\nSummarize for today's context:"),
    ])
    return response.content.strip()


async def generate_cycle_memory(state: dict) -> str:
    """
    Create a 2-sentence memory summary of the current cycle.
    Called after the pipeline completes, before saving to DB.
    """
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.1,
        max_tokens=150,
    )

    weather = state.get("weather_forecast", {})
    prices = state.get("crop_prices", {})
    recs = state.get("top_recommendations", [])
    alerts = state.get("all_alerts", [])

    price_str = ", ".join(f"{k}=₹{v:.0f}" for k, v in list(prices.items())[:4]) if prices else "N/A"
    rec_str = "; ".join(recs[:2]) if recs else "no specific actions"
    alert_str = "; ".join(alerts[:2]) if alerts else "no alerts"

    summary_input = (
        f"Weather: {weather.get('Condition', 'N/A')}, {weather.get('Temperature', '?')}°C, "
        f"{weather.get('Humidity', '?')}% humidity\n"
        f"Prices: {price_str}\n"
        f"Top actions: {rec_str}\n"
        f"Alerts: {alert_str}"
    )

    response = await llm.ainvoke([
        SystemMessage(content="Write exactly 2 sentences summarizing today's farm intelligence cycle. Be specific and factual."),
        HumanMessage(content=summary_input),
    ])
    return response.content.strip()
