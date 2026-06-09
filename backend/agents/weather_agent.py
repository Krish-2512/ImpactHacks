import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural meteorologist specializing in Northeast India farming.
You provide practical, clear farming advice based on weather data for farmers in Assam, Meghalaya, Manipur, and surrounding states.
Consider: monsoon patterns, hill farming, rice cultivation, and vegetable crops common to the region.
Be concise and actionable. Avoid jargon."""


def _extract_list(text: str, keyword: str) -> list[str]:
    lines = text.split("\n")
    alerts = []
    capture = False
    for line in lines:
        if keyword.lower() in line.lower():
            capture = True
            continue
        if capture and line.strip().startswith(("-", "•", "*", "1", "2", "3")):
            clean = re.sub(r"^[-•*\d\.\s]+", "", line).strip()
            if clean:
                alerts.append(clean)
        elif capture and line.strip() == "":
            continue
        elif capture and line.strip() and not line.strip().startswith(("-", "•", "*")):
            break
    return alerts


async def run(state: AgentState) -> AgentState:
    start = time.time()
    w = state["weather_forecast"]
    crops = state.get("farm_state", {}).get("primary_crops", ["tomato", "brinjal", "cabbage"])

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.3,
        max_tokens=800,
    )

    user_msg = f"""Weather forecast for today (Northeast India):
- Temperature: {w.get('Temperature', 'N/A'):.1f}°C
- Humidity: {w.get('Humidity', 'N/A'):.1f}%
- Wind Speed: {w.get('Wind_Speed', 'N/A'):.1f} km/h
- Precipitation: {w.get('Precipitation', 'N/A'):.1f} mm
- Condition: {w.get('Condition', 'N/A')}

Farmer's crops: {', '.join(crops)}

Provide:
1. Weather Interpretation (2 sentences)
2. Planting Advice (1-2 sentences)
3. Irrigation Advice (1-2 sentences)
4. Alerts (bullet list of any warnings, or "None" if clear)"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content
    alerts = _extract_list(text, "Alert") or _extract_list(text, "Warning")

    return {
        **state,
        "weather_interpretation": text,
        "planting_advice": text,
        "irrigation_advice": text,
        "weather_alerts": alerts,
    }
