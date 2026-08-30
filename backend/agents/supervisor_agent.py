import re
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.config import settings

SYSTEM_PROMPT = """You are the chief agricultural intelligence supervisor for Northeast Indian smallholder farmers.
Synthesize weather, market, and advisory reports into one clear, unified farm report.
Write in a warm, encouraging tone accessible to farmers with basic literacy.
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


def _build_decision_graph(state: AgentState) -> dict:
    """Build structured data for frontend decision graph visualization."""
    w = state.get("weather_forecast", {})
    condition = w.get("Condition", "Unknown")
    humidity = w.get("Humidity", 0)

    weather_status = "warn" if state.get("weather_alerts") else "ok"
    disease_status = "warn" if state.get("pest_warnings") else "ok"
    market_status = "warn" if state.get("price_alerts") else "ok"

    decisions = state.get("sell_hold_decisions", {})
    top_decision = next(iter(decisions.values()), "HOLD") if decisions else "HOLD"
    action_status = "action" if top_decision == "SELL" else "ok"

    return {
        "nodes": [
            {"id": "weather",  "label": "Weather",      "value": condition,   "detail": f"{humidity}% humidity", "status": weather_status},
            {"id": "disease",  "label": "Disease Risk",  "value": "High" if float(humidity or 0) > 80 else "Low",  "detail": "; ".join(state.get("pest_warnings", [])[:1]) or "No active alerts", "status": disease_status},
            {"id": "market",   "label": "Market",        "value": f"₹{int(next(iter(state.get('crop_prices', {}).values()), 0))}/qtl", "detail": state.get("best_selling_window", "") or "Assess before selling", "status": market_status},
            {"id": "action",   "label": "Today's Action","value": top_decision, "detail": state.get("top_recommendations", ["No action needed"])[0], "status": action_status},
        ],
        "edges": [
            {"from": "weather", "to": "action"},
            {"from": "disease", "to": "action"},
            {"from": "market",  "to": "action"},
        ],
    }


async def run(state: AgentState) -> AgentState:
    t0 = time.perf_counter()

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

    # Inject farmer memory context if available
    memory_section = ""
    memory_ctx = state.get("memory_context", "").strip()
    if memory_ctx:
        memory_section = f"\nFARMER HISTORY (previous cycles):\n{memory_ctx}\n(Use this context to give more personalised, consistent advice)\n"

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_POWER,
        temperature=0.3,
        max_tokens=1200,
    )

    user_msg = f"""Synthesize the following into a unified daily farm intelligence report:{memory_section}

WEATHER ANALYSIS:
{state.get('weather_interpretation', 'N/A')}
Planting: {state.get('planting_advice', 'N/A')}
Irrigation: {state.get('irrigation_advice', 'N/A')}

MARKET INTELLIGENCE:
{state.get('market_analysis', 'N/A')}
Market Decisions:
{decisions_text or '  (none)'}
Best Window: {state.get('best_selling_window', 'N/A')}

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

    # Average confidence across all agents
    confs = [
        state.get("weather_confidence", 0.7),
        state.get("market_confidence", 0.7),
        state.get("advisory_confidence", 0.7),
    ]
    supervisor_confidence = round(sum(confs) / len(confs), 2)

    decision_graph = _build_decision_graph({**state, "top_recommendations": recommendations})

    elapsed = (time.perf_counter() - t0) * 1000
    timings = {**state.get("agent_timings", {}), "supervisor": round(elapsed, 1)}

    return {
        **state,
        "final_report": text,
        "all_alerts": all_alerts,
        "top_recommendations": recommendations,
        "supervisor_confidence": supervisor_confidence,
        "decision_graph": decision_graph,
        "agent_timings": timings,
    }
