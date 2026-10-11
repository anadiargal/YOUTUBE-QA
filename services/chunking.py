"""
CHUNKING

Why chunk at all?
    * Embedding models and LLM prompts have size limits.
    * One embedding per whole video would be a blurry "average" of every topic,
      so search could not find the specific minute that answers a question.
    * Small, focused chunks => precise retrieval => precise timestamps.

Why overlap?
    Ideas do not respect chunk boundaries. If "Supervised learning is a type of
    ML ..." ends one chunk and "... trained on labeled data" starts the next,
    neither chunk alone contains the full definition. Repeating the last
    `chunk_overlap` tokens of a chunk at the start of the next one means a
    sentence cut at a boundary is still whole in at least one chunk.

How we avoid destroying context:
    We never cut in the middle of a transcript segment (~20 s of speech).
    Chunks are made of WHOLE segments, so every chunk also has an exact
    start_time / end_time for citations.
"""
import config
from utils.helpers import estimate_tokens


def create_chunks(
    segments: list[dict],
    video_id: str,
    chunk_size: int = config.DEFAULTS["chunk_size"],
    chunk_overlap: int = config.DEFAULTS["chunk_overlap"],
) -> list[dict]:
    """
    Returns chunks shaped like:
        {"video_id": "...", "chunk_id": 5, "start_time": 312.0, "end_time": 334.0, "text": "..."}
    """
    chunk_size = max(50, int(chunk_size))
    # Overlap must be clearly smaller than the chunk, or we would never move forward.
    chunk_overlap = max(0, min(int(chunk_overlap), chunk_size // 2))

    tokens = [estimate_tokens(s["text"]) for s in segments]
    chunks: list[dict] = []
    i, n = 0, len(segments)

    while i < n:
        # 1) Grow the chunk with whole segments until the size budget is reached.
        j, total = i, 0
        while j < n and (total + tokens[j] <= chunk_size or j == i):
            total += tokens[j]
            j += 1

        chunks.append({
            "video_id": video_id,
            "chunk_id": len(chunks),
            "start_time": segments[i]["start"],
            "end_time": segments[j - 1]["end"],
            "text": " ".join(s["text"] for s in segments[i:j]),
        })
        if j >= n:
            break

        # 2) Step back to re-include ~chunk_overlap tokens at the start of the next chunk.
        k, shared = j, 0
        while k > i + 1 and shared + tokens[k - 1] <= chunk_overlap:
            k -= 1
            shared += tokens[k]
        i = max(k, i + 1)  # always move forward

    return chunks
