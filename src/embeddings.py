"""Local, free embedding model (no API key, no per-call cost).

Uses sentence-transformers/all-MiniLM-L6-v2 (~80MB, CPU-friendly, runs fine
inside a GitHub Actions runner in a few seconds).
"""
from __future__ import annotations

from functools import lru_cache

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]
