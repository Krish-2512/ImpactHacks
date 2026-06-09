import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are the chief agricultural intelligence supervisor for Northeast Indian smallholder farmers.
Synthesize the weather, market, and advisory reports into one clear, unified farm report.
Write in a warm, encouraging tone that is accessible to farmers with basic literacy.
Be specific about actions — avoid vague advice."""


def _extract_action_items(text: str) -> list[str]:
    items = []
    in_list = False
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^(\d+[\.\)]|[-•*])\s+", stripped):
            clean = re.sub(r"^(\d+[\.\)]|[-•*])\s+", "", stripped).strip()
            if clean:
                items.append(clean)
                in_list = True
        elif in_list and stripped == "":
            continue
        elif in_list and not re.match(r"^(\d+[\.\)]|[-•*])\s+", stripped):
            in_list = False
    return items[:5]


async def run(state: AgentState) -> AgentState:
    decisions_text = "\n".join(
        f"  - {crop.title()}: {decision}"
        for crop, decision in state.get("sell_hold_decisions", {}).items()
    )
    all_alerts_raw = (
        state.get("weather_alerts", []) +
        state.get("price_alerts", []) +
        state.get("pest_warnings", [])
    )
    all_alerts = list(dict.fromkeys(a for a in all_alerts_raw if a.strip()))

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_POWER,
        temperature=0.3,
        max_tokens=1200,
    )

    user_msg = f"""Synthesize the following agent outputs into a unified daily farm intelligence report:

WEATHER ANALYSIS:
{state.get('weather_interpretation', 'N/A')}

MARKET INTELLIGENCE:
{state.get('market_analysis', 'N/A')}
Market Decisions:
{decisions_text or '  (none)'}

CROP ADVISORY:
{state.get('crop_advisory', 'N/A')}

ACTIVE ALERTS:
{chr(10).join(f'  - {a}' for a in all_alerts) if all_alerts else '  None'}

Create a unified report with:
1. Executive Summary (3-4 sentences covering today's key situation)
2. Top 5 Action Items (numbered, specific, actionable for today)
3. Critical Alerts (if any — flag as URGENT)
4. This Week's Outlook (2 sentences)"""

    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    text = response.content
    recommendations = _extract_action_items(text)

    return {
        **state,
        "final_report": text,
        "all_alerts": all_alerts,
        "top_recommendations": recommendations,
    }
