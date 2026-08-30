import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural meteorologist for Northeast India.
Structure your response EXACTLY with these four labelled sections:

WEATHER INTERPRETATION:
[2 sentences explaining what today's conditions mean for farming]

PLANTING ADVICE:
[1-2 sentences on what to plant, transplant, or avoid today]

IRRIGATION ADVICE:
[1-2 sentences on watering — irrigate or skip, and why]

ALERTS:
- [specific warning, or write "None" if conditions are safe]"""


def _parse_section(text: str, label: str) -> str:
    """Extract content under a labelled section heading."""
    pattern = rf"{re.escape(label)}:\s*\n(.*?)(?=\n[A-Z ]+:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    # Line-by-line fallback
    lines = text.split("\n")
    capturing, collected = False, []
    for line in lines:
        if label.lower() in line.lower() and ":" in line:
            capturing = True
            continue
        if capturing:
            if re.match(r"^[A-Z][A-Z ]+:\s*$", line.strip()):
                break
            collected.append(line)
    return "\n".join(collected).strip()


def _extract_alerts(text: str) -> list[str]:
    alerts_text = _parse_section(text, "ALERTS")
    lines = [re.sub(r"^[-•*\d\.\s]+", "", l).strip() for l in alerts_text.split("\n") if l.strip()]
    return [l for l in lines if l and l.lower() not in ("none", "none.", "no alerts", "no alerts.")]


async def run(state: AgentState) -> AgentState:
    t0 = time.perf_counter()
    w = state["weather_forecast"]
    crops = state.get("farm_state", {}).get("primary_crops", ["tomato", "brinjal", "cabbage"])

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.3,
        max_tokens=800,
    )

    def _f(v, fallback=0.0):
        try:
            return f"{float(v):.1f}"
        except (TypeError, ValueError):
            return str(fallback)

    user_msg = f"""Today's weather forecast (Northeast India):
- Temperature: {_f(w.get('Temperature'))}°C
- Humidity: {_f(w.get('Humidity'))}%
- Wind Speed: {_f(w.get('Wind_Speed'))} km/h
- Precipitation: {_f(w.get('Precipitation'))} mm
- Condition: {w.get('Condition', 'N/A')}

Farmer's crops: {', '.join(crops)}"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content

    weather_interp = _parse_section(text, "WEATHER INTERPRETATION") or text[:400]
    planting       = _parse_section(text, "PLANTING ADVICE")
    irrigation     = _parse_section(text, "IRRIGATION ADVICE")
    alerts         = _extract_alerts(text)

    # Higher confidence when using SARIMAX vs seasonal fallback
    data_source = w.get("_source", "fallback")
    confidence = 0.88 if data_source == "sarimax" else 0.65

    elapsed = (time.perf_counter() - t0) * 1000
    timings = {**state.get("agent_timings", {}), "weather": round(elapsed, 1)}

    return {
        **state,
        "weather_interpretation": weather_interp,
        "planting_advice": planting,
        "irrigation_advice": irrigation,
        "weather_alerts": alerts,
        "weather_confidence": confidence,
        "agent_timings": timings,
    }
