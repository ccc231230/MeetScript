"""ASR (Automatic Speech Recognition) service using Aliyun Bailian Paraformer."""

import json
import os
import time
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class ASRService:
    """Aliyun Bailian Paraformer ASR with speaker diarization."""

    def __init__(self):
        self._api_key = settings.DASHSCOPE_API_KEY.get_secret_value()

    async def upload_audio_to_dashscope(self, local_file_path: str) -> str:
        """Upload a local audio file to DashScope's file storage and return a
        publicly accessible URL usable by the Transcription API.

        This solves the "publicly accessible URL" requirement for local dev
        environments where MinIO is only reachable inside Docker.

        Steps:
          1. Upload to DashScope via Files.upload(purpose='inference')
          2. Retrieve the file metadata via Files.get() to obtain the OSS URL
          3. Return the presigned OSS URL
        """
        import dashscope
        from dashscope import Files

        dashscope.api_key = self._api_key

        file_name = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)

        # Step 1: Upload
        upload_resp = Files.upload(
            file_path=local_file_path,
            purpose="inference",
        )
        if upload_resp.status_code != 200:
            raise RuntimeError(
                f"DashScope file upload failed (HTTP {upload_resp.status_code}): "
                f"{upload_resp.message}"
            )

        uploaded = (upload_resp.output or {}).get("uploaded_files", [])
        if not uploaded:
            failed = (upload_resp.output or {}).get("failed_uploads", [])
            raise RuntimeError(
                f"DashScope file upload returned no files. "
                f"Failed: {failed}"
            )

        file_id = uploaded[0]["file_id"]

        # Step 2: Retrieve URL
        get_resp = Files.get(file_id=file_id)
        if get_resp.status_code != 200:
            raise RuntimeError(
                f"DashScope file retrieval failed (HTTP {get_resp.status_code})"
            )

        file_url = (get_resp.output or {}).get("url")
        if not file_url:
            raise RuntimeError("DashScope file retrieval returned no URL")

        return file_url

    async def submit_transcription(
        self,
        audio_url: str,
        source_language: str = "zh",
        enable_diarization: bool = True,
        speaker_count: Optional[int] = None,
    ) -> dict:
        """Submit an async ASR transcription job.

        Args:
            audio_url: Publicly accessible audio file URL (or DashScope file URL).
            source_language: Language code (zh, en, ja, etc.).
            enable_diarization: Enable speaker diarization.
            speaker_count: Expected number of speakers (optional hint).

        Returns:
            Dictionary with task_id and status.
        """
        import dashscope
        from dashscope.audio.asr import Transcription

        dashscope.api_key = self._api_key

        params = {
            "model": settings.DEFAULT_ASR_MODEL,
            "file_urls": [audio_url],
            "language_hints": [source_language],
            "diarization_enabled": enable_diarization,
        }

        if speaker_count:
            params["speaker_count"] = speaker_count

        try:
            response = Transcription.async_call(**params)
            return {
                "task_id": response.output.task_id,
                "status": response.output.task_status,
                "request_id": getattr(response, "request_id", None),
            }
        except Exception as e:
            raise RuntimeError(f"ASR submission failed: {str(e)}") from e

    async def poll_transcription(self, task_id: str) -> dict:
        """Poll the status of an async ASR job.

        Returns dict with:
        - status: PENDING / SUCCESS / FAILED
        - results: list of transcript segments (if SUCCESS)
        - usage: token usage info
        """
        import dashscope
        from dashscope.audio.asr import Transcription

        dashscope.api_key = self._api_key

        try:
            response = Transcription.fetch(task=task_id)
            output = response.output

            result = {
                "task_id": task_id,
                "status": output.task_status,
                "request_id": getattr(response, "request_id", None),
                "results": [],
                "usage": {},
            }

            if output.task_status in ("SUCCESS", "SUCCEEDED"):
                results = []
                output_results = getattr(output, "results", None)

                if output_results is not None:
                    # ── "SUCCESS" format: inline results ───────────
                    if isinstance(output_results, dict):
                        transcriptions = output_results.get("transcripts", [])
                        for transcript in transcriptions:
                            channel_results = transcript.get("channel_results", [])
                            for ch in channel_results:
                                sentences = ch.get("sentences", [])
                                for sent in sentences:
                                    results.append({
                                        "channel_id": ch.get("channel_id", 0),
                                        "speaker_id": sent.get("speaker_id", "SPEAKER_00"),
                                        "start_ms": sent.get("begin_time", 0),
                                        "end_ms": sent.get("end_time", 0),
                                        "text": sent.get("text", ""),
                                        "confidence": sent.get("confidence", 1.0),
                                    })

                    # ── "SUCCEEDED" format: download transcript JSON ─
                    elif isinstance(output_results, list) and output_results:
                        import json
                        import urllib.request

                        for item in output_results:
                            if not isinstance(item, dict):
                                continue
                            transcript_url = item.get("transcription_url")
                            if not transcript_url and "output" in item:
                                transcript_url = item["output"].get("transcription_url")
                            if not transcript_url:
                                continue

                            with urllib.request.urlopen(transcript_url) as resp:
                                data = json.loads(resp.read().decode("utf-8"))

                            for transcript in data.get("transcripts", []):
                                for sent in transcript.get("sentences", []):
                                    speaker = sent.get("speaker_id", 0)
                                    results.append({
                                        "channel_id": transcript.get("channel_id", 0),
                                        "speaker_id": f"SPEAKER_{int(speaker):02d}",
                                        "start_ms": sent.get("begin_time", 0),
                                        "end_ms": sent.get("end_time", 0),
                                        "text": sent.get("text", ""),
                                        "confidence": 0.9,
                                    })

                result["results"] = results
                result["usage"] = {
                    "input_tokens": getattr(output, "usage", {}).get("input_tokens", 0) if hasattr(output, "usage") else 0,
                    "output_tokens": getattr(output, "usage", {}).get("output_tokens", 0) if hasattr(output, "usage") else 0,
                    "total_tokens": getattr(output, "usage", {}).get("total_tokens", 0) if hasattr(output, "usage") else 0,
                }

            elif output.task_status == "FAILED":
                result["error"] = getattr(output, "message", "Unknown error")

            return result

        except Exception as e:
            raise RuntimeError(f"ASR poll failed for task {task_id}: {str(e)}") from e

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: int = 5,
        max_wait: int = 600,
    ) -> dict:
        """Poll until ASR job completes or times out.

        Args:
            task_id: The ASR task ID.
            poll_interval: Seconds between polls.
            max_wait: Maximum seconds to wait.

        Returns:
            Final result dict.
        """
        elapsed = 0
        while elapsed < max_wait:
            result = await self.poll_transcription(task_id)
            status = result.get("status")

            if status in ("SUCCESS", "SUCCEEDED"):
                return result
            elif status == "FAILED":
                raise RuntimeError(f"ASR failed: {result.get('error', 'Unknown')}")

            await asyncio_sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"ASR timed out after {max_wait}s for task {task_id}")


async def asyncio_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


# Singleton
asr_service = ASRService()
