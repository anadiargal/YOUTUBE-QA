"""
RETRIEVAL

Question -> embedding -> nearest chunks -> relevance check.

Why top-K?
    We cannot send the whole transcript to the LLM (cost, limits, and noise).
    We send only the K chunks most similar to the question (default 4).

Why a relevance threshold?
    Vector search ALWAYS returns K results, even for a question the video never
    discusses ("Who invented the Transformer?" in a cooking video). Those
    results are just the "least unrelated" chunks. Without a threshold we would
    hand them to the LLM as if they were evidence - the root cause of
    hallucinated, ungrounded answers. Chunks scoring below the threshold are
    dropped; if nothing survives, the app refuses WITHOUT calling the LLM.
"""
from dataclasses import dataclass, field

from services import embeddings, vector_store


@dataclass
class RetrievedChunk:
    chunk_id: int
    start_time: float
    end_time: float
    text: str
    score: float


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)  # relevant chunks, in video order
    best_score: float = 0.0                                      # best similarity, even if below threshold


def retrieve(question: str, index, top_k: int, threshold: float) -> RetrievalResult:
    query_vec = embeddings.embed_query(question)
    hits = vector_store.search(index, query_vec, k=top_k)
    if not hits:
        return RetrievalResult()

    candidates = [
        RetrievedChunk(
            chunk_id=int(doc.metadata["chunk_id"]),
            start_time=float(doc.metadata["start_time"]),
            end_time=float(doc.metadata["end_time"]),
            text=doc.page_content,
            score=score,
        )
        for doc, score in hits
    ]
    best = max(c.score for c in candidates)
    relevant = [c for c in candidates if c.score >= threshold]
    relevant.sort(key=lambda c: c.start_time)  # chronological order reads more naturally
    return RetrievalResult(chunks=relevant, best_score=best)
