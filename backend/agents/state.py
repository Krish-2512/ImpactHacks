from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict):
    # --- FetchingAgent outputs ---
    cycle_id: str
    weather_forecast: Dict[str, Any]       # {Temperature, Humidity, Wind_Speed, Precipitation, Condition}
    crop_prices: Dict[str, float]          # {brinjal, cabbage, lemon, tomato}
    farm_state: Dict[str, Any]             # user profile info (crops, location)

    # --- WeatherAgent outputs ---
    weather_interpretation: str
    planting_advice: str
    irrigation_advice: str
    weather_alerts: List[str]

    # --- MarketAgent outputs ---
    market_analysis: str
    sell_hold_decisions: Dict[str, str]    # {brinjal: "SELL", tomato: "HOLD", ...}
    price_alerts: List[str]
    best_selling_window: str

    # --- AdvisoryAgent outputs ---
    rag_query: str
    crop_advisory: str
    pest_warnings: List[str]

    # --- SupervisorAgent outputs ---
    final_report: str
    all_alerts: List[str]
    top_recommendations: List[str]

    # --- Meta ---
    error: Optional[str]
