"""
Token counting — estimates LLM token count without calling the API.

Uses a simple character-based heuristic: ~4 chars per token for English/mixed text.
This is accurate enough for budget enforcement (±10%) without adding tiktoken dependency.
"""


def count_tokens(text: str) -> int:
    """Estimate token count for a string (4 chars ≈ 1 token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget. Cuts at sentence boundary where possible."""
    if count_tokens(text) <= max_tokens:
        return text

    char_limit = max_tokens * 4
    truncated = text[:char_limit]

    # Try to end at a sentence boundary
    for sep in (". ", "\n", " "):
        idx = truncated.rfind(sep)
        if idx > char_limit * 0.7:   # don't truncate too aggressively
            return truncated[:idx + len(sep)].rstrip() + " [truncated]"

    return truncated.rstrip() + " [truncated]"
