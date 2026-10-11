"""Offline tests (no API keys needed):  python -m pytest -q   or   python tests/test_core.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from services import chunking, transcript, vector_store
from services.qa import _refine_citation, _split_sources, _is_refusal
from services.retriever import RetrievedChunk
from prompts.qa_prompt import REFUSAL_MESSAGE
from utils.errors import InvalidURLError
from utils.validators import extract_video_id


def test_video_ids():
    vid = "dQw4w9WgXcQ"
    for url in (f"https://www.youtube.com/watch?v={vid}&t=5", f"https://youtu.be/{vid}",
                f"youtube.com/embed/{vid}", f"https://www.youtube.com/shorts/{vid}"):
        assert extract_video_id(url) == vid
    for bad in ("", "hello", "https://example.com/watch?v=dQw4w9WgXcQ", "https://youtube.com/watch?v=short"):
        try:
            extract_video_id(bad)
            assert False, bad
        except InvalidURLError:
            pass


def test_cleaning_and_segments():
    assert transcript.clean_text("[Music] &amp; so >> hello\nworld ♪") == "& so hello world"
    raw = [{"text": f"line {i}", "start": i * 4.0, "duration": 4.0} for i in range(20)]
    segs = transcript.build_segments(raw, segment_seconds=20)
    assert segs[0]["start"] == 0 and segs[0]["end"] == 20.0 and len(segs) == 4


def make_segments(n=60):
    return [{"start": i * 20.0, "end": i * 20.0 + 20, "text": " ".join(f"w{i}_{k}" for k in range(40))} for i in range(n)]


def test_chunking_overlap_and_progress():
    segs = make_segments()
    chunks = chunking.create_chunks(segs, "vid", chunk_size=300, chunk_overlap=100)
    assert chunks[0]["start_time"] == 0 and chunks[-1]["end_time"] == segs[-1]["end"]
    assert all(c["chunk_id"] == i for i, c in enumerate(chunks))
    for a, b in zip(chunks, chunks[1:]):
        assert b["start_time"] > a["start_time"]          # always moves forward
        assert b["start_time"] <= a["end_time"]            # neighbouring chunks overlap (or touch)
    assert any(b["start_time"] < a["end_time"] for a, b in zip(chunks, chunks[1:]))


def test_vector_store_threshold_math():
    from langchain_core.embeddings import FakeEmbeddings
    chunks = chunking.create_chunks(make_segments(10), "vid", 200, 50)
    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(len(chunks), 16)).astype("float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    index = vector_store.build_index(chunks, vecs, FakeEmbeddings(size=16))
    hits = vector_store.search(index, vecs[2], k=3)
    assert hits[0][0].metadata["chunk_id"] == 2 and abs(hits[0][1] - 1.0) < 1e-4   # cosine to itself = 1


def test_sources_and_refusal_parsing():
    body, nums = _split_sources("Supervised learning uses labels.\nSOURCES: 1, 3")
    assert body == "Supervised learning uses labels." and nums == [1, 3]
    assert _is_refusal(REFUSAL_MESSAGE) and _is_refusal(f"'{REFUSAL_MESSAGE}'")
    assert not _is_refusal("Supervised learning uses labels.")


def test_citation_refinement_is_tight():
    segs = make_segments(10)
    segs[4]["text"] = "supervised learning means training on labeled data"
    chunk = RetrievedChunk(0, 0.0, 200.0, "...", 0.9)
    cite = _refine_citation("Supervised learning is training on labeled data.", chunk, segs)
    assert cite["start"] == 80.0 and cite["end"] <= 120.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
