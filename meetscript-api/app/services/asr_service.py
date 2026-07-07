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

        Uses raw requests.post() instead of the DashScope SDK to have full
        control over timeouts and error handling.
        """
        import requests

        file_name = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)

        # Step 1: Upload file via raw HTTP POST
        url = "https://dashscope.aliyuncs.com/api/v1/files"
        logger = __import__("logging").getLogger(__name__)
        logger.warning(
            "[ASR] Uploading %s (%d bytes) to DashScope...",
            file_name, file_size,
        )

        try:
            with open(local_file_path, "rb") as f:
                response = requests.post(
                    url,
                    files=[("files", (file_name, f))],
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Accept": "application/json; charset=utf-8",
                    },
                    timeout=(30, 300),  # (connect, read)
                )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"DashScope file upload timed out after 300s "
                f"(file: {file_name}, size: {file_size})"
            )
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"DashScope file upload connection failed: {e}"
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope file upload failed (HTTP {response.status_code}): "
                f"{response.text[:500]}"
            )

        resp_data = response.json()
        data = resp_data.get("data", resp_data)
        uploaded = data.get("uploaded_files", [])
        if not uploaded:
            failed = data.get("failed_uploads", [])
            raise RuntimeError(
                f"DashScope file upload returned no files. "
                f"Response: {response.text[:500]}"
            )

        file_id = uploaded[0]["file_id"]
        logger.warning("[ASR] File uploaded, id=%s", file_id)

        # Step 2: Retrieve file URL
        get_url = f"https://dashscope.aliyuncs.com/api/v1/files/{file_id}"
        try:
            get_resp = requests.get(
                get_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json; charset=utf-8",
                },
                timeout=(10, 60),
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"DashScope file retrieval timed out for id={file_id}"
            )

        if get_resp.status_code != 200:
            raise RuntimeError(
                f"DashScope file retrieval failed (HTTP {get_resp.status_code})"
            )

        get_data = get_resp.json().get("data", get_resp.json())
        file_url = get_data.get("url")
        if not file_url:
            raise RuntimeError(
                f"DashScope file retrieval returned no URL: "
                f"{get_resp.text[:500]}"
            )

        logger.warning("[ASR] File URL retrieved: %s...", file_url[:80])
        return file_url

    async def submit_transcription(
        self,
        audio_url: str,
        source_language: str = "zh",
        enable_diarization: bool = True,
        speaker_count: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> dict:
        """Submit an async ASR transcription job.

        Args:
            audio_url: Publicly accessible audio file URL (or DashScope file URL).
            source_language: Language code (zh, en, ja, etc.).
            enable_diarization: Enable speaker diarization.
            speaker_count: Expected number of speakers (optional hint).
            model_name: Model ID to use. Falls back to DEFAULT_ASR_MODEL.

        Returns:
            Dictionary with task_id and status.
        """
        import dashscope
        from dashscope.audio.asr import Transcription

        dashscope.api_key = self._api_key

        resolved_model = model_name or settings.DEFAULT_ASR_MODEL

        params = {
            "model": resolved_model,
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
