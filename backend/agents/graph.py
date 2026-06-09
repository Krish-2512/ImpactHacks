from langgraph.graph import StateGraph, END
from backend.agents.state import AgentState
from backend.agents import (
    fetching_agent,
    weather_agent,
    market_agent,
    advisory_agent,
    supervisor_agent,
)


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetching",   fetching_agent.run)
    graph.add_node("weather",    weather_agent.run)
    graph.add_node("market",     market_agent.run)
    graph.add_node("advisory",   advisory_agent.run)
    graph.add_node("supervisor", supervisor_agent.run)

    graph.set_entry_point("fetching")
    graph.add_edge("fetching",   "weather")
    graph.add_edge("weather",    "market")
    graph.add_edge("market",     "advisory")
    graph.add_edge("advisory",   "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()


agent_graph = build_graph()
