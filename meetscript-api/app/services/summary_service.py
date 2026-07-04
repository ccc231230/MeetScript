"""LLM summary service using Aliyun Bailian Qwen."""

import json
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

# Default prompt templates
SUMMARY_PROMPT_TEMPLATE = """你是一个专业的会议纪要助手。请根据以下会议转录文本，生成一份结构化的会议纪要。

要求：
1. 提取会议主题和关键讨论点
2. 列出重要决策和决议
3. 识别行动项和责任人
4. 标注后续跟进事项
5. 使用中文输出

会议转录文本：
{transcript}

请按以下格式输出JSON：
{{
  "title": "会议主题",
  "key_points": ["要点1", "要点2", ...],
  "decisions": ["决策1", "决策2", ...],
  "action_items": [
    {{"task": "任务描述", "assignee": "负责人", "deadline": "截止时间"}}
  ],
  "follow_ups": ["跟进事项1", "跟进事项2", ...],
  "summary": "200字以内的简短总结"
}}
"""


class SummaryService:
    """LLM-based meeting summary generation using Qwen."""

    def __init__(self):
        self._api_key = settings.DASHSCOPE_API_KEY.get_secret_value()

    async def generate_summary(
        self,
        transcript: str,
        model: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> dict:
        """Generate a meeting summary from transcript text.

        Args:
            transcript: Full meeting transcript text.
            model: Model name (default: qwen-max).
            custom_prompt: Custom prompt template override.

        Returns:
            Dict with structured summary and usage info.
        """
        import dashscope
        from dashscope import Generation

        dashscope.api_key = self._api_key

        model_name = model or settings.DEFAULT_SUMMARY_MODEL
        prompt = custom_prompt or SUMMARY_PROMPT_TEMPLATE
        full_prompt = prompt.format(transcript=transcript)

        try:
            response = Generation.call(
                model=model_name,
                messages=[
                    {"role": "user", "content": full_prompt},
                ],
                result_format="message",
                temperature=0.3,
                top_p=0.8,
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                usage = response.usage if hasattr(response, "usage") else {}

                # Try to parse JSON from response
                try:
                    # Extract JSON from markdown code blocks if present
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    summary_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: treat the entire response as summary text
                    summary_data = {
                        "title": "会议纪要",
                        "key_points": [],
                        "decisions": [],
                        "action_items": [],
                        "follow_ups": [],
                        "summary": content,
                    }

                return {
                    "summary": summary_data,
                    "model_used": model_name,
                    "usage": {
                        "input_tokens": usage.get("input_tokens", 0) if usage else 0,
                        "output_tokens": usage.get("output_tokens", 0) if usage else 0,
                        "total_tokens": usage.get("total_tokens", 0) if usage else 0,
                    },
                    "request_id": getattr(response, "request_id", None),
                }
            else:
                raise RuntimeError(
                    f"Summary API error: code={response.status_code}, message={response.message}"
                )

        except Exception as e:
            raise RuntimeError(f"Summary generation failed: {str(e)}") from e

    async def extract_action_items(
        self,
        transcript: str,
        model: Optional[str] = None,
    ) -> dict:
        """Extract only action items from transcript."""
        prompt = """从以下会议转录文本中，提取所有行动项和任务分配。

请按JSON格式输出：
{
  "action_items": [
    {"task": "任务描述", "assignee": "负责人", "deadline": "截止时间"}
  ]
}

会议转录文本：
{transcript}
"""
        return await self.generate_summary(transcript, model, prompt)

    async def generate_minutes(
        self,
        transcript: str,
        speakers: Optional[list[str]] = None,
        model: Optional[str] = None,
    ) -> dict:
        """Generate detailed meeting minutes grouped by speaker."""
        speaker_info = ""
        if speakers:
            speaker_info = f"\n参会者：{', '.join(speakers)}"

        prompt = f"""你是一个专业的会议记录员。请根据会议转录文本生成详细的会议记录。

格式要求：
1. 按讨论顺序记录
2. 标注每段发言的说话人和关键观点
3. 最后生成会议总结

{speaker_info}

会议转录文本：
{{transcript}}

请输出结构化的会议记录。"""
        return await self.generate_summary(transcript, model, prompt)


# Singleton
summary_service = SummaryService()
