"""
JudgeAgent — Reflection / Quality-Control layer.

Reviews the supervisor's final_report and top_recommendations for:
  1. Factual consistency with raw data (weather, prices, decisions)
  2. Missing critical information
  3. Internal conflicts (e.g. "sell tomatoes" but tomato price is at a low)
  4. Overconfident or hallucinated claims

Verdicts:
  pass   — report is sound; no changes
  flag   — issues found; confidence adjusted, issues added to alerts
  reject — serious errors; use judge's revised_recommendations instead

Uses GROQ_MODEL_POWER for accuracy (this is the final gate before the user sees output).
"""
import json
import logging
import time
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a quality-control judge for an agricultural AI system.
Your job is to fact-check the AI's recommendations against the raw data provided.

Check for:
1. Factual consistency — do recommendations match the actual prices, weather, decisions?
2. Missing info — are there urgent alerts that the report ignores?
3. Internal conflicts — e.g., "harvest now" but market says WAIT; "irrigate heavily" but heavy rain forecast
4. Overconfident claims — recommendations stated as certain when data is insufficient

Return ONLY valid JSON:
{
  "verdict": "pass" | "flag" | "reject",
  "issues": ["issue 1", "issue 2"],
  "confidence_adjustment": 0.0,
  "revised_recommendations": []
}

verdict guide:
- pass: no significant issues (confidence_adjustment = 0.0, revised_recommendations = [])
- flag: 1-2 minor issues (confidence_adjustment: 0.05–0.15, revised_recommendations: [])
- reject: major factual errors (confidence_adjustment: 0.20+, provide revised_recommendations)
"""


async def run(state: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()

    final_report = state.get("final_report", "")
    if not final_report:
        # Nothing to judge yet
        return {
            "judge_output": {
                "verdict": "pass",
                "issues": [],
                "confidence_adjustment": 0.0,
                "revised_recommendations": [],
                "skipped": True,
            }
        }

    # Build a concise data summary for the judge
    prices = state.get("crop_prices", {})
    price_str = "; ".join(f"{c}: ₹{p}" for c, p in list(prices.items())[:5]) or "N/A"
    decisions = state.get("sell_hold_decisions", {})
    decision_str = "; ".join(f"{c}: {d}" for c, d in decisions.items()) or "N/A"
    weather = state.get("weather_forecast", {})
    weather_str = (
        f"{weather.get('Condition','?')}, {weather.get('Temperature','?')}°C, "
        f"{weather.get('Humidity','?')}% humidity, {weather.get('Precipitation','?')}mm rain"
    )
    alerts = state.get("all_alerts", [])
    alerts_str = "; ".join(alerts[:5]) or "None"
    recs = state.get("top_recommendations", [])

    user_msg = f"""Raw Data:
- Weather: {weather_str}
- Prices (INR/quintal): {price_str}
- Market decisions: {decision_str}
- Active alerts: {alerts_str}

AI Report (excerpt, first 800 chars):
{final_report[:800]}

Top Recommendations:
{chr(10).join(f"{i+1}. {r}" for i, r in enumerate(recs))}

Review the report and recommendations for factual accuracy and consistency."""

    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_POWER,
            temperature=0.1,
            max_tokens=500,
        )
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        judge_output = json.loads(raw.strip())

        # Sanitize
        verdict = judge_output.get("verdict", "pass")
        if verdict not in ("pass", "flag", "reject"):
            verdict = "pass"
        adjustment = float(judge_output.get("confidence_adjustment", 0.0))
        adjustment = max(0.0, min(0.3, adjustment))   # clamp [0, 0.3]

        judge_output["verdict"] = verdict
        judge_output["confidence_adjustment"] = adjustment

    except Exception as e:
        logger.warning("Judge failed (%s): %s", type(e).__name__, e)
        judge_output = {
            "verdict": "pass",
            "issues": [],
            "confidence_adjustment": 0.0,
            "revised_recommendations": [],
            "error": str(e),
        }

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    verdict = judge_output.get("verdict", "pass")
    issues = judge_output.get("issues", [])
    adjustment = judge_output.get("confidence_adjustment", 0.0)

    logger.info("Judge [%s ms]: verdict=%s issues=%d adj=%.2f", elapsed_ms, verdict, len(issues), adjustment)

    # Apply verdict to state
    updates: dict[str, Any] = {
        "judge_output":  judge_output,
        "agent_timings": {**state.get("agent_timings", {}), "judge": elapsed_ms},
    }

    # If flagged or rejected: adjust confidence and surface issues as alerts
    if verdict in ("flag", "reject") and issues:
        new_conf = max(0.1, state.get("supervisor_confidence", 0.7) - adjustment)
        updates["supervisor_confidence"] = round(new_conf, 2)
        current_alerts = state.get("all_alerts", [])
        updates["all_alerts"] = list(dict.fromkeys(current_alerts + [f"[Judge] {i}" for i in issues]))

    # If rejected: replace recommendations with judge's revised set
    if verdict == "reject":
        revised = judge_output.get("revised_recommendations", [])
        if revised:
            updates["top_recommendations"] = revised

    return updates
