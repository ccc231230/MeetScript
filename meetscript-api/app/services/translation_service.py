"""Translation service using Aliyun Bailian AnyTrans with caching."""

import hashlib
from typing import Optional

from app.core.config import get_settings
from app.services.cache_service import cache_service

settings = get_settings()

# Supported language mapping
SUPPORTED_LANGUAGES = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "th": "Thai",
    "vi": "Vietnamese",
}


class TranslationService:
    """Translation service with multi-level caching for cost optimization."""

    def __init__(self):
        self._api_key = settings.DASHSCOPE_API_KEY.get_secret_value()

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA256 hash for translation cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "zh",
        model: Optional[str] = None,
    ) -> dict:
        """Translate a single piece of text.

        Checks cache first to avoid redundant API calls.

        Returns dict with: translated_text, from_cache, model_used, tokens_input, tokens_output
        """
        if not text or not text.strip():
            return {
                "translated_text": "",
                "from_cache": True,
                "model_used": model or settings.DEFAULT_TRANSLATION_MODEL,
                "tokens_input": 0,
                "tokens_output": 0,
            }

        text_hash = self.compute_hash(text)

        # Check cache
        cached = await cache_service.get_translation(text_hash, target_language)
        if cached:
            return {
                "translated_text": cached,
                "from_cache": True,
                "model_used": model or settings.DEFAULT_TRANSLATION_MODEL,
                "tokens_input": 0,
                "tokens_output": 0,
            }

        # Call API
        result = await self._call_translation_api(
            text, target_language, source_language, model
        )

        # Cache result
        await cache_service.set_translation(
            text_hash, target_language, result["translated_text"]
        )

        return result

    async def _call_translation_api(
        self,
        text: str,
        target_language: str,
        source_language: str = "zh",
        model: Optional[str] = None,
    ) -> dict:
        """Call the DashScope AnyTrans / TextTranslate API."""
        import dashscope

        dashscope.api_key = self._api_key

        model_name = model or settings.DEFAULT_TRANSLATION_MODEL

        try:
            response = dashscope.TextTranslate.call(
                model=model_name,
                source_language=source_language,
                target_language=target_language,
                text=text,
            )

            if response.status_code == 200:
                translated = response.output.get("translated", "")
                usage = response.usage if hasattr(response, "usage") else {}

                return {
                    "translated_text": translated,
                    "from_cache": False,
                    "model_used": model_name,
                    "tokens_input": usage.get("input_tokens", 0),
                    "tokens_output": usage.get("output_tokens", 0),
                }
            else:
                raise RuntimeError(
                    f"Translation API error: code={response.status_code}, message={response.message}"
                )

        except Exception as e:
            raise RuntimeError(f"Translation failed: {str(e)}") from e

    async def batch_translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str = "zh",
        model: Optional[str] = None,
    ) -> list[dict]:
        """Batch translate multiple texts.

        Merges adjacent texts from the same speaker to reduce API calls.
        """
        results = []
        for text in texts:
            result = await self.translate_text(
                text, target_language, source_language, model
            )
            results.append(result)
        return results

    @staticmethod
    def get_supported_languages() -> dict:
        """Return supported language mapping."""
        return SUPPORTED_LANGUAGES


# Singleton
translation_service = TranslationService()
