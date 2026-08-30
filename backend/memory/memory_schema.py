from typing import TypedDict, List


class FarmerMemoryDoc(TypedDict):
    """One memory entry per agent cycle — stored in MongoDB farmer_memory collection."""
    farmer_id: str
    cycle_id: str
    date: str               # ISO: 2025-01-15
    weather_summary: str    # Condition + temp short summary
    market_summary: str     # Key sell/hold decisions
    recommendation_summary: str  # Top action items from that cycle
    disease_alerts: List[str]    # Pest/disease warnings flagged
    memory_text: str        # LLM-generated 2-sentence summary for injection
