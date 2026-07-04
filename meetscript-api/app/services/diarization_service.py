"""Speaker diarization service for candidate name matching."""

import re
from typing import Optional


class DiarizationService:
    """Maps speaker labels to identifiable names through candidate matching."""

    # Default 8-color palette for speaker visualization (hex colors)
    SPEAKER_COLORS = [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
        "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    ]

    @staticmethod
    def assign_speaker_color(speaker_index: int) -> str:
        """Assign a consistent color for a speaker based on index."""
        return DiarizationService.SPEAKER_COLORS[speaker_index % len(DiarizationService.SPEAKER_COLORS)]

    @staticmethod
    def match_candidates(
        subtitles: list[dict],
        candidates: list[str],
    ) -> dict[str, list[str]]:
        """Match speaker labels to candidate names by searching subtitle text.

        Args:
            subtitles: List of subtitle dicts with speaker_label and text.
            candidates: List of candidate names to search for.

        Returns:
            Mapping of speaker_label → list of candidate names found.
        """
        # Group texts by speaker
        speaker_texts: dict[str, list[str]] = {}
        for sub in subtitles:
            label = sub.get("speaker_label", "SPEAKER_00")
            text = sub.get("text", "")
            if label not in speaker_texts:
                speaker_texts[label] = []
            speaker_texts[label].append(text)

        # Search for candidate names in each speaker's text
        speaker_candidates: dict[str, list[str]] = {}
        for label, texts in speaker_texts.items():
            combined = " ".join(texts)
            matched = []
            for candidate in candidates:
                # Check for the full name or parts of it
                name_parts = candidate.split()
                if any(part in combined for part in name_parts) or candidate in combined:
                    matched.append(candidate)
            if matched:
                speaker_candidates[label] = matched

        return speaker_candidates

    @staticmethod
    def mark_candidate_subtitles(
        subtitles: list[dict],
        candidates: list[str],
    ) -> list[dict]:
        """Mark subtitles that contain candidate names as is_candidate=True.

        Returns the updated subtitles list with is_candidate flag set.
        """
        for sub in subtitles:
            text = sub.get("text", "")
            for candidate in candidates:
                name_parts = candidate.split()
                # Check if any significant name part appears in text
                for part in name_parts:
                    if len(part) >= 3 and part in text:  # Only match parts >= 3 chars
                        sub["is_candidate"] = True
                        break
                if sub.get("is_candidate"):
                    break
        return subtitles

    @staticmethod
    def normalize_speaker_labels(
        subtitles: list[dict],
        name_mapping: Optional[dict[str, str]] = None,
    ) -> list[dict]:
        """Replace raw speaker labels (SPEAKER_00) with human-readable names.

        Args:
            subtitles: Subtitle dicts with speaker_label.
            name_mapping: Optional mapping of raw_label → display_name.

        Returns:
            Subtitles with normalized speaker_label.
        """
        for sub in subtitles:
            label = sub.get("speaker_label", "SPEAKER_00")
            if name_mapping and label in name_mapping:
                sub["speaker_label"] = name_mapping[label]
        return subtitles


# Singleton
diarization_service = DiarizationService()
