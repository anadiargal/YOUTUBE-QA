"""
TRANSCRIPT INGESTION

What is a transcript?
    YouTube stores captions as a list of tiny snippets:
        {"text": "so supervised learning is", "start": 312.4, "duration": 2.9}
    Each snippet knows WHEN it was said. We keep that timestamp all the way
    through the pipeline, because it is what lets an answer link back to the
    exact moment in the video (citations).

Steps in this file:
    1. fetch_raw_transcript()  - download snippets from YouTube
    2. clean_text()            - remove caption artifacts ([Music], >>, HTML entities...)
    3. build_segments()        - merge tiny snippets into readable ~20 s segments
"""
import html
import re

import config
from utils.errors import (
    TranscriptExtractionError,
    TranscriptUnavailableError,
    VideoUnavailableError,
    logger,
)


def fetch_raw_transcript(video_id: str) -> list[dict]:
    """Returns [{'text', 'start', 'duration'}, ...] or raises a friendly AppError."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        try:
            fetched = api.fetch(video_id, languages=list(config.TRANSCRIPT_LANGUAGES))
        except Exception as exc:
            # Preferred languages not available -> fall back to ANY transcript on the video.
            if type(exc).__name__ != "NoTranscriptFound":
                raise
            fetched = next(iter(api.list(video_id))).fetch()

        return [
            {"text": s.text, "start": float(s.start), "duration": float(s.duration)}
            for s in fetched
        ]
    except Exception as exc:
        # Match by class name so this works across youtube-transcript-api versions.
        name = type(exc).__name__
        logger.warning("Transcript fetch failed for %s: %s: %s", video_id, name, exc)
        if name in ("TranscriptsDisabled", "NoTranscriptFound", "StopIteration"):
            raise TranscriptUnavailableError() from exc
        if name in ("VideoUnavailable", "VideoUnplayable", "InvalidVideoId", "AgeRestricted"):
            raise VideoUnavailableError() from exc
        if name in ("RequestBlocked", "IpBlocked"):
            raise TranscriptExtractionError(
                "YouTube is temporarily blocking transcript requests from this network. "
                "Try again later or from a different connection."
            ) from exc
        raise TranscriptExtractionError() from exc


_BRACKET_CUES = re.compile(r"\[[^\]]{1,40}\]|\([^)]{1,40}\)")  # [Music], [Applause], (laughs)
_MUSIC_NOTES = re.compile(r"[♪♫]+")
_SPEAKER_ARROWS = re.compile(r"^\s*(>>+|-)\s*|\s>>+\s")
_WHITESPACE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize one caption snippet."""
    text = html.unescape(text)                 # "&amp;#39;" -> "'"
    text = _BRACKET_CUES.sub(" ", text)        # sound cues are not speech
    text = _MUSIC_NOTES.sub(" ", text)
    text = _SPEAKER_ARROWS.sub(" ", text)      # ">>" speaker-change markers
    text = text.replace("\n", " ")
    return _WHITESPACE.sub(" ", text).strip()


def build_segments(raw: list[dict], segment_seconds: int | None = None) -> list[dict]:
    """
    Clean the raw snippets and merge them into display segments:
        [{'start': 312.0, 'end': 334.5, 'text': 'Supervised learning is ...'}, ...]
    """
    segment_seconds = segment_seconds or config.SEGMENT_SECONDS

    cleaned = []
    for snip in raw:
        text = clean_text(snip["text"])
        if not text:
            continue
        # Auto-captions often repeat the previous line; skip exact repeats.
        if cleaned and cleaned[-1]["text"] == text:
            continue
        cleaned.append({"text": text, "start": snip["start"], "end": snip["start"] + snip["duration"]})

    segments: list[dict] = []
    current: dict | None = None
    for snip in cleaned:
        if current is None:
            current = dict(snip)
        elif snip["start"] - current["start"] >= segment_seconds:
            segments.append(current)
            current = dict(snip)
        else:
            current["text"] += " " + snip["text"]
            current["end"] = max(current["end"], snip["end"])
    if current:
        segments.append(current)
    return segments
