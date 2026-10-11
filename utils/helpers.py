"""Small formatting helpers used by the services and the UI."""
import html
import re
from datetime import datetime


def format_timestamp(seconds: float) -> str:
    """312 -> '05:12', 3725 -> '1:02:05'."""
    s = int(max(0, seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def estimate_tokens(text: str) -> int:
    """
    Cheap token estimate (~1.3 tokens per English word). Chunking only needs a
    rough size, so we avoid a tokenizer dependency / API call here.
    """
    return max(1, int(len(text.split()) * 1.3))


def format_views(n) -> str:
    if not n:
        return ""
    n = int(n)
    for limit, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if n >= limit:
            return f"{n / limit:.1f}".rstrip("0").rstrip(".") + f"{suffix} views"
    return f"{n} views"


def format_date(iso: str | None) -> str:
    """'2024-01-10' -> 'Jan 10, 2024' (empty string if unknown)."""
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso[:10])
        return f"{d:%b} {d.day}, {d.year}"
    except ValueError:
        return ""


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def transcript_to_text(segments: list[dict]) -> str:
    """Plain-text export with timestamps, e.g.  [04:32]\\nNow let's talk about..."""
    return "\n\n".join(f"[{format_timestamp(s['start'])}]\n{s['text']}" for s in segments) + "\n"


def highlight_matches(text: str, query: str) -> str:
    """HTML-escape `text` and wrap occurrences of `query` in <mark>."""
    safe = html.escape(text)
    query = (query or "").strip()
    if not query:
        return safe
    pattern = re.compile(re.escape(html.escape(query)), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe)


def inline_markdown_to_html(text: str) -> str:
    """Tiny, safe renderer for chat answers: escapes HTML, supports **bold**, bullets, line breaks."""
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    lines = []
    for line in safe.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            line = "• " + stripped[2:]
        lines.append(line)
    return "<br>".join(lines)
