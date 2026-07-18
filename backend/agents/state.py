from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict):
    # --- Identity ---
    cycle_id: str
    farmer_id: str

    # --- FetchingAgent outputs ---
    weather_forecast: Dict[str, Any]       # {Temperature, Humidity, Wind_Speed, Precipitation, Condition}
    crop_prices: Dict[str, float]          # {brinjal, cabbage, lemon, tomato, ...}
    farm_state: Dict[str, Any]             # user profile info (crops, location)

    # --- WeatherAgent outputs ---
    weather_interpretation: str
    planting_advice: str
    irrigation_advice: str
    weather_alerts: List[str]
    weather_confidence: float

    # --- MarketAgent outputs ---
    market_analysis: str
    sell_hold_decisions: Dict[str, str]    # {brinjal: "SELL", tomato: "HOLD", ...}
    price_alerts: List[str]
    best_selling_window: str
    market_confidence: float

    # --- AdvisoryAgent outputs ---
    rag_query: str
    rag_sources: List[Dict[str, Any]]      # [{text, source, score, tag, retrieval_method}, ...]
    crop_advisory: str
    pest_warnings: List[str]
    advisory_confidence: float

    # --- SupervisorAgent outputs ---
    final_report: str
    all_alerts: List[str]
    top_recommendations: List[str]
    supervisor_confidence: float
    decision_graph: Dict[str, Any]

    # --- Timing (ms per node) ---
    agent_timings: Dict[str, float]

    # --- Memory (Phase 1 / Phase 3) ---
    memory_context: str                    # LLM summary of semantically retrieved memories
    selected_memories: List[Dict[str, Any]]  # raw memory docs used (semantic retrieval)
    memory_retrieval_query: str            # query used for semantic memory search

    # --- Planner (Phase 5) ---
    planner_decision: Dict[str, Any]       # {selected_tools, intent, reasoning, parallel_groups}
    intent: str                            # short label: "full_analysis" | "market_only" | etc.

    # --- Judge / Reflection (Phase 6) ---
    judge_output: Dict[str, Any]           # {verdict, issues, confidence_adjustment, revised_recommendations}

    # --- Disease / Multimodal (Phase 9) ---
    disease_image_b64: Optional[str]       # base64-encoded leaf image (optional input)
    disease_detection: Dict[str, Any]      # {label, confidence, image_provided, suggestions}

    # --- Scheme info (SchemeTool) ---
    scheme_info: List[Dict[str, Any]]

    # --- Observability (Phase 7) ---
    trace: Dict[str, Any]                  # live trace data accumulated during execution

    # --- Meta ---
    error: Optional[str]
