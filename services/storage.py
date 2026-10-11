"""
Lightweight local persistence (no database server needed).

data/library.json              - analyzed videos + history log
data/transcripts/<id>.json     - cleaned transcript segments + suggested questions
data/indexes/<id>/             - the FAISS index (so re-opening a video needs no embedding calls)
"""
import json
import shutil
from datetime import datetime, timezone

import config
from utils.errors import logger

_LIBRARY = config.DATA_DIR / "library.json"


def _read() -> dict:
    try:
        return json.loads(_LIBRARY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"videos": {}, "history": []}


def _write(data: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _LIBRARY.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_LIBRARY)


def save_video(meta: dict, segments: list[dict], suggested: list[str], settings: dict, num_chunks: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    vid = meta["video_id"]
    config.TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (config.TRANSCRIPT_DIR / f"{vid}.json").write_text(
        json.dumps({"segments": segments, "suggested": suggested}), encoding="utf-8"
    )
    data = _read()
    data["videos"][vid] = {
        **meta,
        "analyzed_at": now,
        "num_chunks": num_chunks,
        "chunk_size": settings["chunk_size"],
        "chunk_overlap": settings["chunk_overlap"],
    }
    data["history"].append({"video_id": vid, "analyzed_at": now})
    data["history"] = data["history"][-200:]
    _write(data)


def load_cached(video_id: str) -> dict | None:
    """Returns {'meta', 'segments', 'suggested'} for a previously analyzed video, else None."""
    entry = _read()["videos"].get(video_id)
    path = config.TRANSCRIPT_DIR / f"{video_id}.json"
    if not entry or not path.exists():
        return None
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"meta": entry, "segments": body["segments"], "suggested": body.get("suggested", [])}


def list_videos() -> list[dict]:
    videos = list(_read()["videos"].values())
    return sorted(videos, key=lambda v: v.get("analyzed_at", ""), reverse=True)


def list_history() -> list[dict]:
    """History events (newest first) joined with video details."""
    data = _read()
    events = []
    for ev in reversed(data["history"]):
        video = data["videos"].get(ev["video_id"])
        if video:
            events.append({**video, "analyzed_at": ev["analyzed_at"]})
    return events


def delete_video(video_id: str) -> None:
    data = _read()
    data["videos"].pop(video_id, None)
    data["history"] = [h for h in data["history"] if h["video_id"] != video_id]
    _write(data)
    (config.TRANSCRIPT_DIR / f"{video_id}.json").unlink(missing_ok=True)
    shutil.rmtree(config.INDEX_DIR / video_id, ignore_errors=True)
    logger.info("Deleted saved video %s", video_id)
