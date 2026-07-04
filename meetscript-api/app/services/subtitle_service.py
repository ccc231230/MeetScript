"""Subtitle management service: generation, alignment, export."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subtitle import Subtitle


class SubtitleService:
    """Subtitle generation, storage, and export."""

    @staticmethod
    async def create_subtitles_from_asr(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        asr_results: list[dict],
        language: str = "zh",
    ) -> list[Subtitle]:
        """Create subtitle records from ASR results.

        Args:
            db: Database session.
            meeting_id: Meeting UUID.
            asr_results: List of ASR segments with speaker_id, start_ms, end_ms, text, confidence.
            language: Language code.

        Returns:
            List of created Subtitle objects.
        """
        subtitles = []
        for segment in asr_results:
            subtitle = Subtitle(
                meeting_id=meeting_id,
                speaker_label=segment.get("speaker_id", "SPEAKER_00"),
                language=language,
                start_time_ms=segment.get("start_ms", 0),
                end_time_ms=segment.get("end_ms", 0),
                text=segment.get("text", ""),
                confidence=segment.get("confidence", 1.0),
            )
            db.add(subtitle)
            subtitles.append(subtitle)

        await db.flush()
        return subtitles

    @staticmethod
    async def get_meeting_subtitles(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        language: Optional[str] = None,
        speaker_label: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        """Get paginated subtitles for a meeting with optional filters."""
        from sqlalchemy import func

        query = select(Subtitle).where(Subtitle.meeting_id == meeting_id)

        if language:
            query = query.where(Subtitle.language == language)
        if speaker_label:
            query = query.where(Subtitle.speaker_label == speaker_label)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Order by time
        query = query.order_by(Subtitle.start_time_ms)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def update_subtitle(
        db: AsyncSession,
        subtitle_id: uuid.UUID,
        speaker_label: Optional[str] = None,
        text: Optional[str] = None,
        is_candidate: Optional[bool] = None,
    ) -> Optional[Subtitle]:
        """Update a subtitle entry."""
        result = await db.execute(select(Subtitle).where(Subtitle.id == subtitle_id))
        subtitle = result.scalar_one_or_none()
        if not subtitle:
            return None

        if speaker_label is not None:
            subtitle.speaker_label = speaker_label
        if text is not None:
            subtitle.text = text
        if is_candidate is not None:
            subtitle.is_candidate = is_candidate

        await db.flush()
        return subtitle

    @staticmethod
    def generate_srt(subtitles: list[Subtitle]) -> str:
        """Generate SRT format from subtitles."""
        lines = []
        for i, sub in enumerate(subtitles, 1):
            start = SubtitleService._ms_to_srt_time(sub.start_time_ms)
            end = SubtitleService._ms_to_srt_time(sub.end_time_ms)
            speaker = sub.speaker_label.replace("SPEAKER_", "")
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(f"[{speaker}] {sub.text}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_vtt(subtitles: list[Subtitle]) -> str:
        """Generate WebVTT format from subtitles."""
        lines = ["WEBVTT", ""]
        for i, sub in enumerate(subtitles, 1):
            start = SubtitleService._ms_to_vtt_time(sub.start_time_ms)
            end = SubtitleService._ms_to_vtt_time(sub.end_time_ms)
            speaker = sub.speaker_label.replace("SPEAKER_", "")
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(f"<v {speaker}>{sub.text}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_json(subtitles: list[Subtitle]) -> str:
        """Generate JSON format from subtitles."""
        import json

        data = [
            {
                "index": i,
                "speaker": sub.speaker_label,
                "start_ms": sub.start_time_ms,
                "end_ms": sub.end_time_ms,
                "text": sub.text,
                "confidence": sub.confidence,
                "is_candidate": sub.is_candidate,
            }
            for i, sub in enumerate(subtitles, 1)
        ]
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def generate_txt(subtitles: list[Subtitle]) -> str:
        """Generate plain text format from subtitles."""
        lines = []
        current_speaker = None
        for sub in subtitles:
            if sub.speaker_label != current_speaker:
                speaker = sub.speaker_label.replace("SPEAKER_", "")
                lines.append(f"\n## 发言人 {speaker}\n")
                current_speaker = sub.speaker_label
            lines.append(sub.text)
        return "\n".join(lines).strip()

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _ms_to_srt_time(ms: int) -> str:
        """Convert milliseconds to SRT timestamp format: HH:MM:SS,mmm"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    @staticmethod
    def _ms_to_vtt_time(ms: int) -> str:
        """Convert milliseconds to VTT timestamp format: HH:MM:SS.mmm"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


# Singleton
subtitle_service = SubtitleService()
