"""
BaseTool ABC — every capability in the system implements this interface.

The planner agent uses `name` and `description` to decide which tools to invoke.
`input_schema` is a JSON Schema dict that documents what the tool expects from AgentState.
`run(state)` takes the full current state and returns a partial-state dict (delta).
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    # Subclasses must define these at class level
    name: str = ""
    description: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool against the current pipeline state.

        Args:
            state: Full AgentState dict (read-only by convention).

        Returns:
            Partial dict with only the keys this tool writes.
            The caller merges this into the running state.
        """

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"

    def to_planner_description(self) -> str:
        """Compact string fed to the planner LLM."""
        return f"{self.name}: {self.description}"
