"""Token counting and billing service."""

import hashlib
from decimal import Decimal
from typing import Optional

from app.core.config import get_settings
from app.models.token_usage import TokenUsage

settings = get_settings()

# ── Pricing table (CNY per 1000 tokens) ────────────────────────────
PRICING = {
    # ASR
    "paraformer-v2": {"input": 0.0, "output": 0.0, "unit": "hour", "price_per_hour": 2.8},
    # Translation
    "anytrans": {"input": 0.0, "output": 0.0, "unit": "char", "price_per_char": 0.00005},
    # LLM Summary
    "qwen-max": {"input": 0.04, "output": 0.12},  # per 1k tokens
    "qwen-plus": {"input": 0.02, "output": 0.06},
    "qwen-turbo": {"input": 0.008, "output": 0.024},
    # Default fallback
    "default": {"input": 0.02, "output": 0.06},
}


class TokenService:
    """Token counting, cost calculation, and usage tracking."""

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Compute a stable hash for translation caching."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def estimate_tokens_locally(text: str, model: str = "default") -> int:
        """Local token estimation using tiktoken (for UI budget display only)."""
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Rough heuristic: 1 token ≈ 2 characters for CJK, 1 token ≈ 4 chars for English
            # Use a conservative estimate
            return max(1, len(text) // 2)

    @staticmethod
    def _get_pricing(model_name: str) -> dict:
        """Get pricing configuration for a model."""
        return PRICING.get(model_name, PRICING["default"])

    @staticmethod
    def calculate_cost(model_name: str, tokens_input: int = 0, tokens_output: int = 0) -> float:
        """Calculate cost based on model pricing."""
        pricing = TokenService._get_pricing(model_name)

        if pricing.get("unit") == "hour":
            return 0.0  # ASR cost calculated separately by duration

        if pricing.get("unit") == "char":
            # Translation cost based on characters
            return tokens_input * pricing.get("price_per_char", 0.00005)

        # LLM cost per 1000 tokens
        input_cost = (tokens_input / 1000.0) * pricing["input"]
        output_cost = (tokens_output / 1000.0) * pricing["output"]
        return round(input_cost + output_cost, 6)

    @staticmethod
    def calculate_asr_cost(duration_seconds: float, model_name: str = "paraformer-v2") -> float:
        """Calculate ASR cost based on audio duration."""
        pricing = TokenService._get_pricing(model_name)
        hours = duration_seconds / 3600.0
        return round(hours * pricing.get("price_per_hour", 2.8), 4)

    @staticmethod
    async def record_usage_from_api_response(
        db,
        response: dict,
        context: dict,
    ) -> TokenUsage:
        """Record token usage from a DashScope/API response."""
        usage = response.get("usage", {})
        model_name = context.get("model_name", "default")

        token_usage = TokenUsage(
            user_id=context["user_id"],
            meeting_id=context.get("meeting_id"),
            model_config_id=context.get("model_config_id"),
            operation_type=context["operation_type"],
            tokens_input=usage.get("input_tokens", 0),
            tokens_output=usage.get("output_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            cost=TokenService.calculate_cost(
                model_name,
                tokens_input=usage.get("input_tokens", 0),
                tokens_output=usage.get("output_tokens", 0),
            ),
            request_id=response.get("request_id"),
        )
        db.add(token_usage)
        return token_usage

    @staticmethod
    async def record_usage(
        db,
        user_id,
        operation_type: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model_name: str = "default",
        meeting_id=None,
        model_config_id=None,
        request_id: Optional[str] = None,
        custom_cost: Optional[float] = None,
    ) -> TokenUsage:
        """Record token usage directly."""
        cost = custom_cost if custom_cost is not None else TokenService.calculate_cost(
            model_name, tokens_input, tokens_output
        )
        token_usage = TokenUsage(
            user_id=user_id,
            meeting_id=meeting_id,
            model_config_id=model_config_id,
            operation_type=operation_type,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost=cost,
            request_id=request_id,
        )
        db.add(token_usage)
        return token_usage


# Singleton
token_service = TokenService()
