"""SRT/VTT subtitle format parsing utilities."""

import re
from typing import Optional


def parse_srt(content: str) -> list[dict]:
    """Parse SRT format into structured subtitle segments.

    Args:
        content: SRT file content as string.

    Returns:
        List of {index, start_ms, end_ms, text} dicts.
    """
    segments = []
    pattern = re.compile(
        r"(\d+)\n"
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
        r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\n"
        r"((?:.+\n?)+?)(?=\n\n|\Z)",
        re.MULTILINE,
    )

    for match in pattern.finditer(content.strip()):
        index = int(match.group(1))
        start_ms = _time_to_ms(
            int(match.group(2)), int(match.group(3)),
            int(match.group(4)), int(match.group(5)),
        )
        end_ms = _time_to_ms(
            int(match.group(6)), int(match.group(7)),
            int(match.group(8)), int(match.group(9)),
        )
        text = match.group(10).strip()

        segments.append({
            "index": index,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
        })

    return segments


def parse_vtt(content: str) -> list[dict]:
    """Parse WebVTT format into structured subtitle segments."""
    segments = []
    # Remove WEBVTT header
    if content.startswith("WEBVTT"):
        content = content.split("\n", 1)[1] if "\n" in content else ""

    # Remove metadata and comments
    lines = content.strip().split("\n")
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith("NOTE"):
            continue
        cleaned_lines.append(line)

    content = "\n".join(cleaned_lines)

    pattern = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*"
        r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})(?:\s+.*)?\n"
        r"((?:.+\n?)+?)(?=\n\n|\Z)",
        re.MULTILINE,
    )

    for i, match in enumerate(pattern.finditer(content), 1):
        start_ms = _time_to_ms(
            int(match.group(1)), int(match.group(2)),
            int(match.group(3)), int(match.group(4)),
        )
        end_ms = _time_to_ms(
            int(match.group(5)), int(match.group(6)),
            int(match.group(7)), int(match.group(8)),
        )
        text = match.group(9).strip()

        segments.append({
            "index": i,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
        })

    return segments


def _time_to_ms(hours: int, minutes: int, seconds: int, millis: int) -> int:
    """Convert time components to milliseconds."""
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + millis


def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT timestamp: HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def ms_to_vtt_time(ms: int) -> str:
    """Convert milliseconds to VTT timestamp: HH:MM:SS.mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"
