"""URL validation and YouTube video-ID extraction."""
import re
from urllib.parse import parse_qs, urlparse

from utils.errors import InvalidURLError

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YT_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtube-nocookie.com", "www.youtube-nocookie.com",
}


def extract_video_id(url: str) -> str:
    """
    Accepts watch?v=, youtu.be/, /embed/, /shorts/, /live/ links and returns
    the 11-character video ID. Raises InvalidURLError otherwise.
    """
    url = (url or "").strip()
    if not url:
        raise InvalidURLError("Please paste a YouTube video URL first.")
    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    video_id = None

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in _YT_HOSTS:
        if parsed.path == "/watch":
            video_id = (parse_qs(parsed.query).get("v") or [None])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
                video_id = parts[1]

    if video_id and _VIDEO_ID.match(video_id):
        return video_id
    raise InvalidURLError()
