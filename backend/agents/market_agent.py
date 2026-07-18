import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural market analyst for Northeast India.
Structure your response EXACTLY as:

MARKET SUMMARY:
[2 sentences on overall market situation considering weather impact]

DECISIONS:
crop_name: SELL/HOLD/WAIT | reason in 1 sentence | Best window: [timeframe or N/A]

PRICE ALERTS:
- [specific alert, or "None"]

BEST SELLING WINDOW:
[1 sentence: overall best timeframe for selling, e.g. "Sell tomatoes within 2 days, hold cabbage for next week"]"""

CROP_NAMES_HI = {
    "brinjal": "बैगन (Brinjal)",
    "cabbage": "पत्ता गोभी (Cabbage)",
    "lemon": "नींबू (Lemon)",
    "tomato": "टमाटर (Tomato)",
}


def _parse_decisions(text: str, crops: list) -> dict:
    decisions = {}
    for crop in crops:
        pattern = rf"{crop}[^|]*?[:\s]+(SELL|HOLD|WAIT)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            decisions[crop] = match.group(1).upper()
        else:
            # Broader fallback
            for word in ["SELL", "HOLD", "WAIT"]:
                snippet = text[max(0, text.lower().find(crop.lower())-5):][:100]
                if word in snippet.upper():
                    decisions[crop] = word
                    break
            else:
                decisions[crop] = "HOLD"
    return decisions


def _parse_section(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}:\s*\n(.*?)(?=\n[A-Z ]+:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


async def run(state: AgentState) -> AgentState:
    t0 = time.perf_counter()
    prices = state["crop_prices"]
    crops = list(prices.keys())
    w = state.get("weather_forecast", {})

    price_lines = "\n".join(
        f"- {CROP_NAMES_HI.get(c, c)}: ₹{v}/quintal" for c, v in prices.items()
    )

    def _f(v, fallback="N/A"):
        try: return f"{float(v):.1f}"
        except (TypeError, ValueError): return str(fallback)

    weather_context = (
        f"Current weather: {w.get('Condition', 'N/A')}, "
        f"{_f(w.get('Temperature'))}°C, "
        f"{_f(w.get('Humidity'))}% humidity, "
        f"{_f(w.get('Precipitation'))} mm rain"
    )

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_POWER,
        temperature=0.2,
        max_tokens=900,
    )

    user_msg = f"""Current crop price predictions (INR/quintal) for Northeast India:
{price_lines}

{weather_context}
(Consider: rain increases transport difficulty, high humidity reduces shelf life, hot weather increases perishability)

Analyze each crop considering BOTH price and current weather conditions."""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content

    decisions = _parse_decisions(text, crops)

    alerts_section = _parse_section(text, "PRICE ALERTS")
    alerts = [
        re.sub(r"^[-•*\d\.\s]+", "", l).strip()
        for l in alerts_section.split("\n") if l.strip()
    ]
    alerts = [a for a in alerts if a and a.lower() not in ("none", "none.")]
    # Supplement from full text scan
    if not alerts:
        alerts = [
            line.strip("- •*").strip()
            for line in text.split("\n")
            if any(w in line.lower() for w in ["alert", "spike", "drop", "urgent", "crash"])
            and len(line.strip()) > 10
        ][:3]

    best_window = _parse_section(text, "BEST SELLING WINDOW")
    if not best_window:
        # Extract from DECISIONS section
        decisions_text = _parse_section(text, "DECISIONS")
        windows = re.findall(r"Best window:\s*([^\n|]+)", decisions_text, re.IGNORECASE)
        best_window = "; ".join(w.strip() for w in windows if w.strip().lower() != "n/a") or ""

    # Confidence based on price source
    first_price = next(iter(prices.values()), 0)
    confidence = 0.80 if first_price > 0 else 0.50

    elapsed = (time.perf_counter() - t0) * 1000
    timings = {**state.get("agent_timings", {}), "market": round(elapsed, 1)}

    return {
        **state,
        "market_analysis": text,
        "sell_hold_decisions": decisions,
        "price_alerts": alerts[:3],
        "best_selling_window": best_window,
        "market_confidence": confidence,
        "agent_timings": timings,
    }
