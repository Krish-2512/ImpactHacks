from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field
from backend.models.base import MongoBase, PyObjectId


class AgentOutput(MongoBase):
    agent_name: str
    input_summary: str
    output: str
    confidence: Optional[float] = None
    execution_time_ms: int = 0


class AgentCycleDocument(MongoBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    cycle_id: str
    triggered_by: str = "manual"              # "manual" | "scheduled"
    user_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"                   # "running" | "completed" | "failed"
    weather_data: Dict[str, Any] = {}
    price_data: Dict[str, Any] = {}
    agents_output: List[AgentOutput] = []
    final_report: str = ""
    alerts: List[str] = []
    recommendations: List[str] = []
    sell_hold_decisions: Dict[str, str] = {}


class AgentCycleOut(MongoBase):
    id: Optional[str] = Field(default=None, alias="_id")
    cycle_id: str
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    weather_data: Dict[str, Any]
    price_data: Dict[str, Any]
    agents_output: List[AgentOutput]
    final_report: str
    alerts: List[str]
    recommendations: List[str]
    sell_hold_decisions: Dict[str, str]
