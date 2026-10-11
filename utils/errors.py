"""
Friendly application errors.

Every error that can reach the UI is an AppError with a human-readable
`user_message`. Raw Python exceptions are logged, never displayed.
"""
import logging

logger = logging.getLogger("youtube_qa")


class AppError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class InvalidURLError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(
            msg or "That doesn't look like a valid YouTube video link. "
            "Try something like https://www.youtube.com/watch?v=VIDEO_ID"
        )


class VideoUnavailableError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "This video is unavailable (it may be private, removed, or age-restricted).")


class TranscriptUnavailableError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(
            msg or "No transcript is available for this video. "
            "Captions may be disabled — try a video that has captions or subtitles."
        )


class TranscriptExtractionError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "Something went wrong while extracting the transcript. Please try again.")


class EmbeddingError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "The embedding service had a problem. Please try again in a moment.")


class VectorStoreError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "The vector index could not be built or read. Try analyzing the video again.")


class LLMError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "Gemini couldn't generate an answer right now. Please try again.")


class QuestionError(AppError):
    def __init__(self, msg: str = ""):
        super().__init__(msg or "Something went wrong while processing your question. Please try again.")


class ConfigError(AppError):
    pass


def api_error_message(exc: Exception, fallback: str) -> str:
    """Translate a raw Google API exception into a friendly message."""
    text = str(exc).lower()
    if "api key" in text or "api_key" in text or "permission" in text or "401" in text or "403" in text:
        return "The Gemini API key was rejected. Check GOOGLE_API_KEY in your .env file."
    if "429" in text or "quota" in text or "resource_exhausted" in text or "rate" in text:
        return "The Gemini API rate limit was reached. Wait a minute and try again."
    if "timeout" in text or "503" in text or "unavailable" in text or "deadline" in text:
        return "The Gemini API is temporarily unavailable. Please try again shortly."
    return fallback
