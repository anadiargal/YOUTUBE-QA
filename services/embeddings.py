"""
EMBEDDINGS

What is an embedding?
    A list of numbers (a vector) that captures the MEANING of a piece of text.
    "What is supervised learning?" and "learning from labeled examples" end up
    close together in vector space even though they share few words. That is
    what lets us search by meaning instead of by keyword.

We L2-normalize every vector (length = 1). For unit vectors the dot product
equals cosine similarity, a score from about 0 (unrelated) to 1 (same meaning).
"""
import time
from functools import lru_cache

import numpy as np

import config
from utils.errors import ConfigError, EmbeddingError, api_error_message, logger

_BATCH_SIZE = 32


@lru_cache(maxsize=1)
def get_embedding_model():
    """Gemini embedding model wrapped by LangChain."""
    if not config.GOOGLE_API_KEY:
        raise ConfigError("GOOGLE_API_KEY is missing. Add it to your .env file and restart the app.")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=config.EMBEDDING_MODEL, google_api_key=config.GOOGLE_API_KEY)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def embed_documents(texts: list[str]) -> np.ndarray:
    """Embed transcript chunks (task type: retrieval document). Shape: (n_chunks, dim)."""
    model = get_embedding_model()
    out: list[list[float]] = []
    try:
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start:start + _BATCH_SIZE]
            for attempt in range(3):  # simple retry/backoff for rate limits
                try:
                    out.extend(model.embed_documents(batch))
                    break
                except Exception as exc:
                    if attempt == 2 or "429" not in str(exc):
                        raise
                    time.sleep(2 ** attempt * 5)
    except Exception as exc:
        logger.exception("Embedding documents failed")
        raise EmbeddingError(api_error_message(exc, "The embedding service had a problem. Please try again.")) from exc
    return _normalize(np.array(out, dtype="float32"))


def embed_query(question: str) -> np.ndarray:
    """Embed the user's question (task type: retrieval query). Shape: (dim,)."""
    model = get_embedding_model()
    try:
        vec = np.array([model.embed_query(question)], dtype="float32")
    except Exception as exc:
        logger.exception("Embedding query failed")
        raise EmbeddingError(api_error_message(exc, "The embedding service had a problem. Please try again.")) from exc
    return _normalize(vec)[0]
