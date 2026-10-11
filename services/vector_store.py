"""
VECTOR STORE (FAISS)

How are vectors stored?
    FAISS keeps all chunk vectors in one big matrix. A search compares the
    question vector against every row and returns the closest ones. With
    "Inner Product" distance on unit-length vectors, score == cosine similarity.
    (A single video has at most a few hundred chunks, so exact search is instant.)

Alongside each vector we store the chunk text + metadata (video_id, chunk_id,
start_time, end_time) in a LangChain Document. That metadata is how a search
hit turns into a clickable timestamp.
"""
from pathlib import Path

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

import config
from utils.errors import VectorStoreError, logger


def build_index(chunks: list[dict], vectors: np.ndarray, embedder) -> FAISS:
    try:
        text_embeddings = [(c["text"], v.tolist()) for c, v in zip(chunks, vectors)]
        metadatas = [
            {k: c[k] for k in ("video_id", "chunk_id", "start_time", "end_time")} for c in chunks
        ]
        return FAISS.from_embeddings(
            text_embeddings=text_embeddings,
            embedding=embedder,
            metadatas=metadatas,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
    except Exception as exc:
        logger.exception("Building FAISS index failed")
        raise VectorStoreError() from exc


def index_path(video_id: str) -> Path:
    return config.INDEX_DIR / video_id


def save_index(index: FAISS, video_id: str) -> None:
    try:
        path = index_path(video_id)
        path.mkdir(parents=True, exist_ok=True)
        index.save_local(str(path))
    except Exception as exc:
        logger.exception("Saving FAISS index failed")
        raise VectorStoreError() from exc


def load_index(video_id: str, embedder) -> FAISS:
    try:
        # allow_dangerous_deserialization: the pickle file was written by this very app.
        return FAISS.load_local(
            str(index_path(video_id)), embedder,
            allow_dangerous_deserialization=True,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
    except Exception as exc:
        logger.exception("Loading FAISS index failed")
        raise VectorStoreError() from exc


def search(index: FAISS, query_vector: np.ndarray, k: int) -> list[tuple[Document, float]]:
    """Nearest-neighbour search. Returns [(Document, cosine_similarity), ...] best first."""
    try:
        hits = index.similarity_search_with_score_by_vector(query_vector.tolist(), k=k)
        return [(doc, float(score)) for doc, score in hits]
    except Exception as exc:
        logger.exception("FAISS search failed")
        raise VectorStoreError() from exc
