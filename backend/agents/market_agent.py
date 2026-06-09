import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are an expert agricultural market analyst for Northeast India.
You advise smallholder farmers on when to sell, hold, or wait on their crops.
Consider: Guwahati wholesale market rates, transport costs, perishability, storage capacity.
Be direct with SELL/HOLD/WAIT decisions. Explain in simple language."""

CROP_NAMES_HI = {
    "brinjal": "बैगन (Brinjal)",
    "cabbage": "पत्ता गोभी (Cabbage)",
    "lemon": "नींबू (Lemon)",
    "tomato": "टमाटर (Tomato)",
}


def _parse_decisions(text: str, crops: list) -> dict:
    decisions = {}
    for crop in crops:
        for word in ["SELL", "HOLD", "WAIT"]:
            if crop.lower() in text.lower() and word in text.upper():
                decisions[crop] = word
                break
        if crop not in decisions:
            decisions[crop] = "HOLD"
    return decisions


async def run(state: AgentState) -> AgentState:
    prices = state["crop_prices"]
    crops = list(prices.keys())

    price_lines = "\n".join(
        f"- {CROP_NAMES_HI.get(c, c)}: ₹{v}/quintal" for c, v in prices.items()
    )

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_POWER,
        temperature=0.2,
        max_tokens=900,
    )

    user_msg = f"""Current crop price predictions (INR/quintal) for Northeast India:
{price_lines}

For each crop, give:
1. SELL / HOLD / WAIT recommendation
2. Brief reason (1 sentence)
3. Best selling window if HOLD/WAIT

Also provide:
- Overall market summary (2 sentences)
- Any price alerts (significant drops or spikes)"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content

    decisions = _parse_decisions(text, crops)
    alerts = [
        line.strip("- •*").strip()
        for line in text.split("\n")
        if any(word in line.lower() for word in ["alert", "drop", "spike", "urgent", "warning"])
        and len(line.strip()) > 10
    ]

    return {
        **state,
        "market_analysis": text,
        "sell_hold_decisions": decisions,
        "price_alerts": alerts[:3],
        "best_selling_window": "",
    }
