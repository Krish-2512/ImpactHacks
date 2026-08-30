"""
ContextBuilder — assembles structured LLM prompt context from multiple sources.

Priority order when truncating to max_tokens:
  1. User profile (always included — low token cost)
  2. Memory context (summarized history)
  3. Tool outputs (weather, market, disease results)
  4. RAG chunks (retrieved document excerpts — trimmed last)

Usage:
    ctx = (
        ContextBuilder()
        .with_user_profile(user)
        .with_memory(memory_context, budget=400)
        .with_tool_outputs({"weather": weather_dict, "market": market_dict})
        .with_rag_chunks(rag_sources, budget=1200)
        .build(max_tokens=3000)
    )
"""
from __future__ import annotations
from typing import Any
from backend.context.token_counter import count_tokens, truncate_to_budget


class ContextBuilder:

    def __init__(self) -> None:
        self._sections: list[tuple[int, str, str]] = []   # (priority, label, content)

    # ── Fluent builders ──────────────────────────────────────────────────────

    def with_user_profile(self, user: dict[str, Any]) -> "ContextBuilder":
        crops = ", ".join(user.get("primary_crops", [])) or "general"
        location = user.get("location") or "Northeast India"
        farm_size = user.get("farm_size_acres")
        size_str = f", {farm_size} acres" if farm_size else ""
        text = (
            f"Farmer: {user.get('username', 'Farmer')} | "
            f"Location: {location}{size_str} | "
            f"Crops: {crops}"
        )
        self._sections.append((0, "FARMER PROFILE", text))
        return self

    def with_memory(self, memory_context: str, budget: int = 400) -> "ContextBuilder":
        if not memory_context or not memory_context.strip():
            return self
        truncated = truncate_to_budget(memory_context, budget)
        self._sections.append((1, "FARMER HISTORY", truncated))
        return self

    def with_tool_outputs(
        self, outputs: dict[str, Any], budget_per_tool: int = 300
    ) -> "ContextBuilder":
        """
        outputs: dict of tool_name → summary string or dict.
        Dicts are auto-formatted into key: value lines.
        """
        for tool_name, output in outputs.items():
            if not output:
                continue
            if isinstance(output, dict):
                lines = [f"  {k}: {v}" for k, v in output.items() if v]
                text = "\n".join(lines)
            else:
                text = str(output)
            truncated = truncate_to_budget(text, budget_per_tool)
            self._sections.append((2, f"[{tool_name.upper()} OUTPUT]", truncated))
        return self

    def with_rag_chunks(
        self, chunks: list[dict[str, Any]], budget: int = 1200
    ) -> "ContextBuilder":
        if not chunks:
            return self
        parts = []
        used = 0
        for chunk in chunks:
            text = chunk.get("text", "")
            src = chunk.get("source", "")
            score = chunk.get("score", 0.0)
            entry = f"[Source: {src} | score: {score:.2f}]\n{text}"
            entry_tokens = count_tokens(entry)
            if used + entry_tokens > budget:
                break
            parts.append(entry)
            used += entry_tokens
        if parts:
            self._sections.append((3, "KNOWLEDGE BASE", "\n\n".join(parts)))
        return self

    def with_raw(self, label: str, text: str, priority: int = 2, budget: int = 500) -> "ContextBuilder":
        """Escape hatch for arbitrary context sections."""
        if text and text.strip():
            self._sections.append((priority, label, truncate_to_budget(text, budget)))
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self, max_tokens: int = 3000) -> str:
        """
        Assemble all sections into a single context string.
        Sections are included in priority order; low-priority sections are
        dropped first if the total exceeds max_tokens.
        """
        # Sort by priority (ascending = higher importance first)
        sections = sorted(self._sections, key=lambda s: s[0])

        lines: list[str] = []
        used = 0

        for priority, label, content in sections:
            block = f"--- {label} ---\n{content}"
            tokens = count_tokens(block)

            if used + tokens > max_tokens:
                # Try to fit a truncated version for lower-priority blocks
                remaining = max_tokens - used
                if remaining > 50 and priority >= 2:
                    block = f"--- {label} ---\n{truncate_to_budget(content, remaining - 10)}"
                    tokens = count_tokens(block)
                else:
                    continue   # skip entirely

            lines.append(block)
            used += tokens

        return "\n\n".join(lines)

    # ── Class-level factory for agents ────────────────────────────────────────

    @classmethod
    def from_state(cls, state: dict[str, Any], include: list[str] | None = None) -> str:
        """
        Convenience factory: builds context from a full AgentState dict.
        include: list of tool sections to add. Defaults to all available.
        """
        builder = cls()

        farm_state = state.get("farm_state", {})
        builder.with_user_profile(farm_state)

        if memory := state.get("memory_context", ""):
            builder.with_memory(memory)

        tool_outputs: dict[str, Any] = {}
        if include is None or "weather" in include:
            if wi := state.get("weather_interpretation"):
                tool_outputs["weather"] = wi
        if include is None or "market" in include:
            if ma := state.get("market_analysis"):
                tool_outputs["market"] = ma
        if include is None or "disease" in include:
            if dd := state.get("disease_detection", {}):
                if dd.get("label"):
                    tool_outputs["disease"] = f"{dd['label']} ({dd['confidence']*100:.0f}% confidence)"
        if tool_outputs:
            builder.with_tool_outputs(tool_outputs)

        if include is None or "rag" in include:
            if sources := state.get("rag_sources", []):
                builder.with_rag_chunks(sources)

        return builder.build()
