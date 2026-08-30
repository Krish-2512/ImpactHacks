"""
Agriculture Intelligence endpoints — Phase 3.

/intelligence/farm-health      → composite 0-100 score from latest cycle
/intelligence/risk-score       → weather/disease/market risk breakdown
/intelligence/crop-calendar    → AI-generated sowing/irrigation/harvest calendar
/intelligence/decision-impact  → expected profit/risk/water for a crop decision
"""
import asyncio
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db
from backend.config import settings

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _latest_cycle_required(cycle: dict | None):
    if not cycle:
        raise HTTPException(
            status_code=404,
            detail="No completed agent cycle found. Run AI Analysis first.",
        )
    return cycle


async def _get_latest_cycle(user_id, db) -> dict | None:
    return await db["agent_cycles"].find_one(
        {"status": "completed"},
        sort=[("completed_at", -1)],
    )


# ─── Farm Health Score ─────────────────────────────────────────────────────────

@router.get("/farm-health")
async def farm_health_score(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Composite 0-100 health score across Weather, Disease, Market, and Advisory.
    Components:
      - Weather (25 pts): weather_confidence × 25
      - Disease (25 pts): 25 − (5 × pest_warning_count)
      - Market (25 pts): fraction of SELL/HOLD decisions (WAIT penalized)
      - Advisory (25 pts): advisory_confidence × 25
    """
    cycle = _latest_cycle_required(await _get_latest_cycle(current_user["_id"], db))

    confs = cycle.get("confidences", {})

    # Weather component
    weather_pts = round(confs.get("weather", 0.7) * 25, 1)

    # Disease component (alerts reduce score)
    alerts = cycle.get("alerts", [])
    pest_count = sum(1 for a in alerts if any(w in str(a).lower() for w in ["pest", "disease", "blight", "fungal"]))
    disease_pts = max(0, 25 - (pest_count * 5))

    # Market component
    decisions = cycle.get("sell_hold_decisions", {})
    if decisions:
        good = sum(1 for d in decisions.values() if d in ("SELL", "HOLD"))
        market_pts = round((good / len(decisions)) * 25, 1)
    else:
        market_pts = 15.0

    # Advisory component
    advisory_pts = round(confs.get("advisory", 0.7) * 25, 1)

    total = round(weather_pts + disease_pts + market_pts + advisory_pts, 1)

    def _grade(score):
        if score >= 85: return "Excellent", "🟢"
        if score >= 70: return "Good", "🟡"
        if score >= 50: return "Fair", "🟠"
        return "Needs Attention", "🔴"

    grade, emoji = _grade(total)

    return {
        "overall_score": total,
        "grade": grade,
        "emoji": emoji,
        "components": {
            "weather":  {"score": weather_pts, "max": 25, "label": "Weather Conditions"},
            "disease":  {"score": disease_pts,  "max": 25, "label": "Disease/Pest Risk"},
            "market":   {"score": market_pts,   "max": 25, "label": "Market Opportunity"},
            "advisory": {"score": advisory_pts, "max": 25, "label": "Crop Advisory"},
        },
        "cycle_id": cycle.get("cycle_id"),
        "as_of": cycle.get("completed_at"),
    }


# ─── Risk Score ───────────────────────────────────────────────────────────────

@router.get("/risk-score")
async def risk_score(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Three-dimensional risk breakdown: Weather | Disease | Market.
    Returns score 0-100 per dimension (lower = riskier).
    """
    cycle = _latest_cycle_required(await _get_latest_cycle(current_user["_id"], db))

    alerts = cycle.get("alerts", [])
    weather_data = cycle.get("weather_data", {})
    confs = cycle.get("confidences", {})

    # Weather risk
    weather_alerts = [a for a in alerts if "rain" in a.lower() or "wind" in a.lower() or "storm" in a.lower() or "heat" in a.lower()]
    weather_risk_score = max(0, 100 - len(weather_alerts) * 20 - (0 if confs.get("weather", 0) > 0.7 else 15))

    # Disease risk
    disease_alerts = [a for a in alerts if any(w in str(a).lower() for w in ["pest", "disease", "blight", "fungal", "mite"])]
    precip = float(weather_data.get("Precipitation", 0) or 0)
    humidity = float(weather_data.get("Humidity", 0) or 0)
    disease_base = 100 - len(disease_alerts) * 25
    if humidity > 80: disease_base -= 15
    if precip > 20: disease_base -= 10
    disease_risk_score = max(0, disease_base)

    # Market risk
    decisions = cycle.get("sell_hold_decisions", {})
    wait_count = sum(1 for d in decisions.values() if d == "WAIT")
    sell_count = sum(1 for d in decisions.values() if d == "SELL")
    price_alerts_count = sum(1 for a in alerts if "price" in str(a).lower() or "crash" in str(a).lower() or "spike" in str(a).lower())
    market_risk_score = max(0, 100 - wait_count * 10 + sell_count * 5 - price_alerts_count * 15)
    market_risk_score = min(100, market_risk_score)

    def _level(score):
        if score >= 75: return "Low Risk", "🟢"
        if score >= 50: return "Moderate", "🟡"
        if score >= 25: return "High Risk", "🟠"
        return "Critical", "🔴"

    return {
        "weather": {
            "score": round(weather_risk_score, 1),
            **dict(zip(["level", "emoji"], _level(weather_risk_score))),
            "alerts": weather_alerts[:3],
        },
        "disease": {
            "score": round(disease_risk_score, 1),
            **dict(zip(["level", "emoji"], _level(disease_risk_score))),
            "alerts": disease_alerts[:3],
        },
        "market": {
            "score": round(market_risk_score, 1),
            **dict(zip(["level", "emoji"], _level(market_risk_score))),
            "alerts": [a for a in alerts if "price" in str(a).lower()][:3],
        },
        "overall_risk": round((weather_risk_score + disease_risk_score + market_risk_score) / 3, 1),
        "as_of": cycle.get("completed_at"),
    }


# ─── Crop Calendar ─────────────────────────────────────────────────────────────

class CalendarRequest(BaseModel):
    crops: list[str]
    location: str = "Northeast India"
    season: Optional[str] = None  # Kharif / Rabi / Zaid — auto-detected if None


@router.post("/crop-calendar")
async def generate_crop_calendar(
    payload: CalendarRequest,
    _user=Depends(get_current_user),
):
    """
    LLM-generated crop calendar with sowing → fertilizer → irrigation → harvest dates.
    Returns structured JSON with monthly activities.
    """
    today = date.today()
    month_name = today.strftime("%B")

    # Auto-detect season
    month = today.month
    if payload.season:
        season = payload.season
    elif month in (6, 7, 8, 9, 10):
        season = "Kharif (Monsoon)"
    elif month in (11, 12, 1, 2, 3):
        season = "Rabi (Winter)"
    else:
        season = "Zaid (Summer)"

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.3,
        max_tokens=1200,
    )

    system = """You are an expert agricultural advisor for Northeast India.
Generate a detailed crop calendar in JSON format.
Return ONLY valid JSON, no markdown, no explanation."""

    user_msg = f"""Generate a crop calendar for:
Crops: {', '.join(payload.crops)}
Location: {payload.location}
Season: {season}
Current month: {month_name} {today.year}

Return JSON like this:
{{
  "season": "{season}",
  "crops": {{
    "tomato": {{
      "sowing": "Month + week",
      "transplanting": "Month + week",
      "first_fertilizer": "Month + week + type",
      "irrigation_schedule": "e.g. Every 5 days",
      "pest_spray_schedule": "e.g. Every 15 days",
      "harvest_start": "Month",
      "harvest_end": "Month",
      "notes": "1-2 tips specific to Northeast India"
    }}
  }},
  "monthly_tasks": {{
    "July": ["Task 1", "Task 2"],
    "August": ["Task 1"]
  }}
}}"""

    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_msg),
    ])

    import json as _json
    try:
        calendar_data = _json.loads(response.content)
    except Exception:
        # If LLM returned non-JSON, wrap the text
        calendar_data = {"raw": response.content, "parse_error": True}

    return {"calendar": calendar_data, "generated_at": today.isoformat()}


# ─── Decision Impact Analyzer ─────────────────────────────────────────────────

class ImpactRequest(BaseModel):
    crop: str
    action: str     # "grow" | "sell" | "hold" | "skip"
    area_acres: float = 1.0
    budget_inr: Optional[float] = None


@router.post("/decision-impact")
async def decision_impact(
    payload: ImpactRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    For a given crop decision, returns:
    - Expected profit/loss
    - Water usage estimate
    - Risk level
    - What happens if ignored
    - Alternative options
    """
    cycle = await _get_latest_cycle(current_user["_id"], db)
    price_context = ""
    if cycle:
        prices = cycle.get("price_data", {})
        if payload.crop.lower() in prices:
            price_context = f"Current market price: ₹{prices[payload.crop.lower()]:.0f}/quintal"

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL_FAST,
        temperature=0.2,
        max_tokens=800,
    )

    system = """You are an expert agricultural economist for Northeast India.
Return ONLY valid JSON, no markdown. Be realistic with Northeast India crop economics."""

    user_msg = f"""Analyze this farming decision:
Crop: {payload.crop}
Action: {payload.action}
Area: {payload.area_acres} acres
Budget: ₹{payload.budget_inr or 'not specified'}
{price_context}

Return JSON:
{{
  "expected_profit_inr": <number or null>,
  "water_usage_liters_per_acre": <number>,
  "roi_percent": <number or null>,
  "risk_level": "Low/Medium/High",
  "risk_reasons": ["reason1", "reason2"],
  "if_ignored": "What happens if farmer does NOT do this (1 sentence)",
  "alternatives": [
    {{"crop": "alternative crop", "reason": "why better", "expected_profit_inr": <number>}}
  ],
  "confidence": <0.0 to 1.0>
}}"""

    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_msg),
    ])

    import json as _json
    try:
        impact = _json.loads(response.content)
    except Exception:
        impact = {"raw": response.content, "parse_error": True}

    return {
        "crop": payload.crop,
        "action": payload.action,
        "area_acres": payload.area_acres,
        "impact": impact,
    }
