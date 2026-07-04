"""Token counter utility using tiktoken (local estimation only)."""


def estimate_tokens(text: str, model: str = "default") -> int:
    """Estimate token count for a given text using tiktoken.

    Note: This is a rough estimate for UI display only.
    Actual usage should be taken from DashScope API response.
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Heuristic: ~2 chars per token for CJK, ~4 for English
        return max(1, len(text) // 2)


def format_token_count(count: int) -> str:
    """Format token count for display."""
    if count >= 1000000:
        return f"{count / 1000000:.1f}M"
    if count >= 1000:
        return f"{count / 1000:.1f}K"
    return str(count)


def format_cost(cost: float) -> str:
    """Format cost in CNY."""
    if cost >= 1:
        return f"¥{cost:.2f}"
    if cost >= 0.01:
        return f"¥{cost:.4f}"
    return f"¥{cost:.6f}"
