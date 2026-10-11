"""
THE WHOLE RAG PIPELINE IN ONE PLACE (read this file first!)

INGEST (once per video)
    URL -> video id -> transcript -> clean -> segments -> chunks
        -> embeddings -> FAISS index -> suggested questions -> saved to disk

ASK (every question)
    question -> embedding -> top-K similarity search -> relevance threshold
        -> Gemini (context only) -> answer + timestamp sources

The retrieval layer is NEVER bypassed: answer() has no path to Gemini that
does not go through retriever.retrieve().
"""
from typing import Callable

import config
from services import chunking, embeddings, qa, retriever, storage, transcript, vector_store, youtube
from utils.errors import AppError, TranscriptUnavailableError, logger
from utils.validators import extract_video_id

StepCallback = Callable[[str], None]


def ingest(url: str, settings: dict, on_step: StepCallback = lambda m: None) -> dict:
    video_id = extract_video_id(url)                                   # validate URL + extract ID
    embedder = embeddings.get_embedding_model()                        # fail early if the API key is missing

    # Re-use earlier work if this video was analyzed with the same chunk settings.
    cached = storage.load_cached(video_id)
    if (
        cached
        and cached["meta"].get("chunk_size") == settings["chunk_size"]
        and cached["meta"].get("chunk_overlap") == settings["chunk_overlap"]
        and vector_store.index_path(video_id).exists()
    ):
        on_step("Loading saved analysis…")
        return load_video(video_id)

    on_step("Fetching transcript…")
    meta = youtube.get_video_metadata(video_id)
    raw = transcript.fetch_raw_transcript(video_id)

    on_step("Cleaning transcript…")
    segments = transcript.build_segments(raw)
    if not segments:
        raise TranscriptUnavailableError()
    meta["duration"] = meta.get("duration") or int(segments[-1]["end"])

    on_step("Creating chunks…")
    chunks = chunking.create_chunks(segments, video_id, settings["chunk_size"], settings["chunk_overlap"])

    on_step("Generating embeddings…")
    vectors = embeddings.embed_documents([c["text"] for c in chunks])

    on_step("Building vector index…")
    index = vector_store.build_index(chunks, vectors, embedder)
    vector_store.save_index(index, video_id)

    on_step("Preparing suggested questions…")
    suggested = qa.generate_suggested_questions(segments)

    storage.save_video(meta, segments, suggested, settings, num_chunks=len(chunks))
    on_step("Ready ✓")
    return {"meta": meta, "segments": segments, "index": index, "suggested": suggested, "num_chunks": len(chunks)}


def load_video(video_id: str) -> dict:
    """Re-open a previously analyzed video from disk (no transcript/embedding API calls)."""
    cached = storage.load_cached(video_id)
    if not cached:
        raise AppError("Saved data for this video is missing. Please analyze the video again.")
    index = vector_store.load_index(video_id, embeddings.get_embedding_model())
    return {
        "meta": cached["meta"],
        "segments": cached["segments"],
        "index": index,
        "suggested": cached["suggested"],
        "num_chunks": cached["meta"].get("num_chunks", 0),
    }


def answer(question: str, video: dict, settings: dict, on_step: StepCallback = lambda m: None) -> qa.Answer:
    on_step("Searching transcript…")
    on_step("Retrieving relevant context…")
    retrieval = retriever.retrieve(question, video["index"], settings["top_k"], settings["similarity_threshold"])
    logger.info("Question retrieved %d relevant chunks (best score %.2f)", len(retrieval.chunks), retrieval.best_score)
    on_step("Generating answer…")
    return qa.answer_question(question, retrieval, video["segments"])
