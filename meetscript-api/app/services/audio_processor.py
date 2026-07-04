"""Audio preprocessing pipeline using ffmpeg.

Pipeline:
  Input (mp4/mov/wav/mp3/...) → Extract audio → Transcode (16kHz/mono/WAV) →
  Split long audio (>30min) → Quality check → Output segments
"""

import hashlib
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


@dataclass
class AudioSegment:
    """Metadata for a processed audio segment."""

    file_path: str
    index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    md5_hash: str
    quality_warnings: list[str] = field(default_factory=list)


@dataclass
class AudioProcessResult:
    """Result of audio preprocessing."""

    segments: list[AudioSegment]
    original_duration_seconds: float
    total_segments: int
    warnings: list[str] = field(default_factory=list)


class AudioProcessor:
    """Audio preprocessing service: extraction, transcoding, splitting, quality check."""

    def __init__(self):
        self._target_sample_rate = settings.AUDIO_TARGET_SAMPLE_RATE
        self._target_channels = settings.AUDIO_TARGET_CHANNELS
        self._target_format = settings.AUDIO_TARGET_FORMAT
        self._segment_duration = settings.AUDIO_SEGMENT_DURATION
        self._timeout = settings.FFMPEG_TIMEOUT

    def _get_audio_duration(self, file_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            file_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return 0.0
            import json

            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0

    def _compute_md5(self, file_path: str) -> str:
        """Compute MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _run_ffmpeg(self, args: list[str], description: str = "ffmpeg") -> bool:
        """Run ffmpeg command with timeout. Returns True on success."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(f"{description} failed: {result.stderr[:500]}")
            return True
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"{description} timed out after {self._timeout}s")

    def _extract_audio(self, input_path: str, output_path: str) -> None:
        """Extract audio track from video file."""
        self._run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", str(self._target_sample_rate),
                "-ac", str(self._target_channels),
                output_path,
            ],
            description="Audio extraction",
        )

    def _transcode_audio(self, input_path: str, output_path: str) -> None:
        """Transcode audio to target format (16kHz, mono, PCM 16bit WAV)."""
        self._run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", str(self._target_sample_rate),
                "-ac", str(self._target_channels),
                "-sample_fmt", "s16",
                output_path,
            ],
            description="Audio transcoding",
        )

    def _split_audio(self, input_path: str, output_dir: str, segment_prefix: str) -> list[str]:
        """Split audio into segments of configured duration."""
        self._run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-f", "segment",
                "-segment_time", str(self._segment_duration),
                "-c", "copy",
                os.path.join(output_dir, f"{segment_prefix}_%03d.{self._target_format}"),
            ],
            description="Audio segmentation",
        )
        # Collect segment files sorted by index
        segments = sorted(
            [f for f in os.listdir(output_dir) if f.startswith(segment_prefix)],
            key=lambda x: int(x.split("_")[-1].split(".")[0]) if "_" in x else 0,
        )
        return [os.path.join(output_dir, s) for s in segments]

    def _check_audio_quality(self, file_path: str) -> list[str]:
        """Check audio quality and return warnings."""
        warnings = []

        try:
            # Check for silence (detect if >80% is silent)
            result = subprocess.run(
                [
                    "ffmpeg", "-i", file_path,
                    "-af", "silencedetect=noise=-40dB:d=2",
                    "-f", "null", "-",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            silence_lines = [l for l in result.stderr.split("\n") if "silence_duration" in l]
            total_silence = 0.0
            for line in silence_lines:
                if "silence_duration:" in line:
                    try:
                        total_silence += float(line.split("silence_duration:")[1].strip())
                    except ValueError:
                        pass

            duration = self._get_audio_duration(file_path)
            if duration > 0 and (total_silence / duration) > 0.8:
                warnings.append(f"Audio is >80% silent ({total_silence:.1f}s / {duration:.1f}s)")

            # Check RMS level
            result = subprocess.run(
                [
                    "ffmpeg", "-i", file_path,
                    "-af", "volumedetect",
                    "-f", "null", "-",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            for line in result.stderr.split("\n"):
                if "mean_volume" in line:
                    try:
                        mean_vol = float(line.split(":")[1].strip().split()[0])
                        if mean_vol < -40:
                            warnings.append(f"Low audio level (mean volume: {mean_vol:.1f} dB)")
                    except (ValueError, IndexError):
                        pass

        except Exception as e:
            warnings.append(f"Quality check error: {str(e)}")

        return warnings

    def _is_video_file(self, file_path: str) -> bool:
        """Check if the file is a video file (needs audio extraction)."""
        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
        return Path(file_path).suffix.lower() in video_extensions

    def process(self, input_path: str, meeting_id: str = "", work_dir: Optional[str] = None) -> AudioProcessResult:
        """Full audio preprocessing pipeline.

        Args:
            input_path: Path to the original media file.
            meeting_id: Meeting ID for organizing temp files.
            work_dir: Persistent working directory (uses config default if not provided).

        Returns:
            AudioProcessResult with processed segments and metadata.
        """
        if work_dir is None:
            work_dir = settings.AUDIO_WORK_DIR

        os.makedirs(work_dir, exist_ok=True)

        all_warnings: list[str] = []
        segments: list[AudioSegment] = []

        current_path = input_path
        is_video = self._is_video_file(input_path)

        # Step 1: Extract audio from video if needed
        if is_video:
            extracted_path = os.path.join(work_dir, f"{meeting_id}_extracted.wav")
            self._extract_audio(input_path, extracted_path)
            current_path = extracted_path

        # Step 2: Transcode to target format
        transcoded_path = os.path.join(work_dir, f"{meeting_id}_transcoded.{self._target_format}")
        self._transcode_audio(current_path, transcoded_path)
        current_path = transcoded_path

        # Step 3: Check if splitting is needed
        total_duration = self._get_audio_duration(current_path)

        if total_duration > self._segment_duration:
            # Step 4a: Split into segments
            seg_prefix = f"seg_{meeting_id[:8]}"
            self._split_audio(current_path, work_dir, seg_prefix)

            seg_files = sorted(
                [f for f in os.listdir(work_dir) if f.startswith(seg_prefix)],
                key=lambda x: int(x.split("_")[-1].split(".")[0]) if "_" in x else 0,
            )
            seg_files = [os.path.join(work_dir, s) for s in seg_files]

            for i, seg_file in enumerate(seg_files):
                seg_duration = self._get_audio_duration(seg_file)
                warnings = self._check_audio_quality(seg_file)
                all_warnings.extend(warnings)

                segments.append(AudioSegment(
                    file_path=seg_file,
                    index=i,
                    start_seconds=i * self._segment_duration,
                    end_seconds=(i + 1) * self._segment_duration,
                    duration_seconds=seg_duration,
                    sample_rate=self._target_sample_rate,
                    channels=self._target_channels,
                    format=self._target_format,
                    md5_hash=self._compute_md5(seg_file),
                    quality_warnings=warnings,
                ))
        else:
            # Step 4b: Single segment
            warnings = self._check_audio_quality(current_path)
            all_warnings.extend(warnings)

            segments.append(AudioSegment(
                file_path=current_path,
                index=0,
                start_seconds=0.0,
                end_seconds=total_duration,
                duration_seconds=total_duration,
                sample_rate=self._target_sample_rate,
                channels=self._target_channels,
                format=self._target_format,
                md5_hash=self._compute_md5(current_path),
                quality_warnings=warnings,
            ))

        return AudioProcessResult(
            segments=segments,
            original_duration_seconds=total_duration,
            total_segments=len(segments),
            warnings=all_warnings,
        )

    def get_cache_key(self, input_path: str) -> str:
        """Generate a cache key based on file hash and processing parameters."""
        file_hash = self._compute_md5(input_path)
        params_str = f"{self._target_sample_rate}:{self._target_channels}:{self._target_format}:{self._segment_duration}"
        return hashlib.md5(f"{file_hash}:{params_str}".encode()).hexdigest()


# Singleton
audio_processor = AudioProcessor()
