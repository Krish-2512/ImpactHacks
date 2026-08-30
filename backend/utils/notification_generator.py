"""
Rule Engine — converts agent pipeline outputs into actionable notifications.

Priority levels:
  urgent  → disease outbreak, extreme weather, immediate price crash
  high    → SELL opportunity, heavy rain tomorrow, pest warning
  medium  → HOLD advice, mild weather alert, market shift
  low     → general tip, crop calendar reminder

Types:
  weather | market | disease | crop_calendar | scheme | system
"""
from datetime import datetime, timedelta
from typing import Any


# ─── Rules ────────────────────────────────────────────────────────────────────

def _weather_rules(state: dict) -> list[dict]:
    notes = []
    w = state.get("weather_forecast", {})
    alerts = state.get("weather_alerts", [])
    confidence = state.get("weather_confidence", 0.7)

    def _f(v):
        try: return float(v)
        except: return 0.0

    precip   = _f(w.get("Precipitation"))
    temp     = _f(w.get("Temperature"))
    humidity = _f(w.get("Humidity"))
    wind     = _f(w.get("Wind_Speed"))
    cond     = w.get("Condition", "")

    if precip > 40:
        notes.append({
            "type": "weather", "priority": "urgent",
            "title": "Heavy Rainfall Alert",
            "body": f"Expected {precip:.0f}mm rainfall today. Delay irrigation, protect harvested crops, check drainage channels.",
            "confidence": round(confidence, 2),
            "icon": "🌧️",
        })
    elif precip > 15:
        notes.append({
            "type": "weather", "priority": "medium",
            "title": "Moderate Rain Expected",
            "body": f"{precip:.0f}mm rain predicted. Skip irrigation today — soil moisture will be adequate.",
            "confidence": round(confidence, 2),
            "icon": "🌦️",
        })

    if temp > 36:
        notes.append({
            "type": "weather", "priority": "high",
            "title": "Heat Stress Warning",
            "body": f"Temperature {temp:.0f}°C — water plants in early morning, use mulching to retain soil moisture.",
            "confidence": round(confidence, 2),
            "icon": "🌡️",
        })

    if humidity > 85:
        notes.append({
            "type": "disease", "priority": "high",
            "title": "High Fungal Disease Risk",
            "body": f"Humidity at {humidity:.0f}% — conditions ideal for late blight, powdery mildew. Apply preventive fungicide.",
            "confidence": round(confidence, 2),
            "icon": "🍄",
        })

    if wind > 50:
        notes.append({
            "type": "weather", "priority": "high",
            "title": "Strong Wind Alert",
            "body": f"Wind speed {wind:.0f} km/h expected. Stake climbing crops, protect nursery beds.",
            "confidence": round(confidence, 2),
            "icon": "💨",
        })

    if "Thunderstorm" in cond:
        notes.append({
            "type": "weather", "priority": "urgent",
            "title": "Thunderstorm Warning",
            "body": "Thunderstorm expected. Avoid open field work, secure farm equipment, check irrigation systems.",
            "confidence": round(confidence, 2),
            "icon": "⛈️",
        })

    for alert in alerts[:2]:
        if alert and len(alert) > 10:
            notes.append({
                "type": "weather", "priority": "medium",
                "title": "Weather Advisory",
                "body": alert,
                "confidence": round(confidence, 2),
                "icon": "🌤️",
            })

    return notes


def _market_rules(state: dict) -> list[dict]:
    notes = []
    decisions = state.get("sell_hold_decisions", {})
    price_alerts = state.get("price_alerts", [])
    prices = state.get("crop_prices", {})
    best_window = state.get("best_selling_window", "")
    confidence = state.get("market_confidence", 0.7)

    # SELL recommendations are high priority
    sell_crops = [c for c, d in decisions.items() if d == "SELL"]
    if sell_crops:
        price_str = ", ".join(
            f"{c.title()} ₹{int(prices.get(c, 0))}" for c in sell_crops
        )
        notes.append({
            "type": "market", "priority": "high",
            "title": "🟢 SELL Signal — Act Today",
            "body": f"Market conditions are favorable for: {price_str}/quintal. {best_window or 'Consider selling within 24-48 hours.'}",
            "confidence": round(confidence, 2),
            "icon": "📈",
        })

    # WAIT recommendations
    wait_crops = [c for c, d in decisions.items() if d == "WAIT"]
    if wait_crops:
        notes.append({
            "type": "market", "priority": "medium",
            "title": "⏳ WAIT — Prices Expected to Rise",
            "body": f"{', '.join(c.title() for c in wait_crops)} prices are expected to increase. {best_window or 'Hold for better rates.'}",
            "confidence": round(confidence, 2),
            "icon": "⏳",
        })

    # Price alerts
    for alert in price_alerts[:2]:
        if alert and len(alert) > 10:
            priority = "urgent" if any(w in alert.lower() for w in ["crash", "drop", "emergency"]) else "high"
            notes.append({
                "type": "market", "priority": priority,
                "title": "Price Alert",
                "body": alert,
                "confidence": round(confidence, 2),
                "icon": "💰",
            })

    return notes


def _disease_rules(state: dict) -> list[dict]:
    notes = []
    pest_warnings = state.get("pest_warnings", [])
    confidence = state.get("advisory_confidence", 0.7)
    humidity = float(state.get("weather_forecast", {}).get("Humidity", 0) or 0)

    for warning in pest_warnings[:3]:
        if not warning or len(warning) < 10:
            continue
        priority = "urgent" if any(w in warning.lower() for w in ["outbreak", "severe", "critical", "blight"]) else "high"
        notes.append({
            "type": "disease", "priority": priority,
            "title": "Disease/Pest Warning",
            "body": warning,
            "confidence": round(confidence, 2),
            "icon": "🐛",
        })

    # Preventive reminder if high humidity but no specific warning
    if humidity > 80 and not pest_warnings:
        notes.append({
            "type": "disease", "priority": "medium",
            "title": "Preventive Spray Reminder",
            "body": f"Humidity {humidity:.0f}% — good time for prophylactic copper sulfate or neem oil spray to prevent fungal issues.",
            "confidence": 0.75,
            "icon": "💊",
        })

    return notes


def _farm_action_rules(state: dict) -> list[dict]:
    """Generate crop advisory notifications from top recommendations."""
    notes = []
    recs = state.get("top_recommendations", [])
    confidence = state.get("supervisor_confidence", 0.7)

    if recs:
        notes.append({
            "type": "crop_calendar", "priority": "medium",
            "title": "Today's Top Action",
            "body": recs[0],
            "confidence": round(confidence, 2),
            "icon": "🌱",
        })
    if len(recs) > 1:
        notes.append({
            "type": "crop_calendar", "priority": "low",
            "title": "Additional Recommendation",
            "body": recs[1],
            "confidence": round(confidence, 2),
            "icon": "📋",
        })

    return notes


# ─── Main generator ───────────────────────────────────────────────────────────

def generate_notifications(state: dict) -> list[dict]:
    """
    Run all rule functions against the agent state and return notification dicts.
    Called after every agent cycle completes.
    """
    all_notes: list[dict] = []
    all_notes.extend(_weather_rules(state))
    all_notes.extend(_market_rules(state))
    all_notes.extend(_disease_rules(state))
    all_notes.extend(_farm_action_rules(state))

    # Deduplicate by title
    seen_titles: set[str] = set()
    unique = []
    for n in all_notes:
        if n["title"] not in seen_titles:
            seen_titles.add(n["title"])
            unique.append(n)

    # Sort: urgent first, then high, medium, low
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    unique.sort(key=lambda n: priority_order.get(n["priority"], 4))

    return unique


async def persist_notifications(
    db,
    user_id: Any,
    notifications: list[dict],
    cycle_id: str,
    expires_hours: int = 48,
) -> int:
    """Save generated notifications to MongoDB. Returns count inserted."""
    if not notifications:
        return 0

    now = datetime.utcnow()
    docs = []
    for n in notifications:
        docs.append({
            "user_id": user_id,
            "cycle_id": cycle_id,
            "type": n.get("type", "system"),
            "priority": n.get("priority", "low"),
            "title": n.get("title", ""),
            "body": n.get("body", ""),
            "icon": n.get("icon", "📌"),
            "confidence": n.get("confidence", 0.0),
            "is_read": False,
            "created_at": now,
            "expires_at": now + timedelta(hours=expires_hours),
        })

    if docs:
        await db["notifications"].insert_many(docs)

    return len(docs)
