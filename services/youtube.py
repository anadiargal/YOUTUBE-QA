"""
Video metadata (title, channel, views, publish date, duration).

This is best-effort: if metadata can't be fetched we still carry on, because the
transcript is what the RAG pipeline really needs.
"""
import json
import re

import requests

from utils.errors import logger
from utils.helpers import thumbnail_url

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_COOKIES = {"CONSENT": "YES+1"}  # skips the EU cookie-consent interstitial


def _unescape(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except ValueError:
        return value


def get_video_metadata(video_id: str) -> dict:
    meta = {
        "video_id": video_id,
        "title": f"YouTube video {video_id}",
        "channel": "",
        "views": None,
        "published": None,       # "YYYY-MM-DD"
        "duration": None,        # seconds
        "thumbnail": thumbnail_url(video_id),
    }

    # 1) oEmbed: tiny, official, no API key. Gives title + channel.
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            headers=_HEADERS, timeout=8,
        )
        if r.ok:
            data = r.json()
            meta["title"] = data.get("title") or meta["title"]
            meta["channel"] = data.get("author_name") or ""
    except Exception as exc:  # network issues must not break ingestion
        logger.warning("oEmbed failed for %s: %s", video_id, exc)

    # 2) Watch page: scrape views / publish date / duration (fragile, so optional).
    try:
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=_HEADERS, cookies=_COOKIES, timeout=10,
        )
        if r.ok:
            page = r.text
            if m := re.search(r'"lengthSeconds":"(\d+)"', page):
                meta["duration"] = int(m.group(1))
            if m := re.search(r'"viewCount":"(\d+)"', page):
                meta["views"] = int(m.group(1))
            if m := re.search(r'"publishDate":"(\d{4}-\d{2}-\d{2})', page):
                meta["published"] = m.group(1)
            if not meta["channel"] and (m := re.search(r'"ownerChannelName":"([^"]+)"', page)):
                meta["channel"] = _unescape(m.group(1))
    except Exception as exc:
        logger.warning("Watch-page metadata failed for %s: %s", video_id, exc)

    return meta
