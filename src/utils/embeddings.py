"""Embedding model wrapper."""

from functools import lru_cache
from typing import Optional
import numpy as np
from loguru import logger


class EmbeddingModel:
    """Singleton wrapper for sentence-transformers."""

    _instance: Optional["EmbeddingModel"] = None
    _model = None

    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model_name = model_name
        return cls._instance

    @classmethod
    def get_model(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed, using fallback")
                cls._model = "fallback"
        return cls._model

    @staticmethod
    def encode_texts(texts: list[str], model=None) -> np.ndarray:
        if model is None:
            model = EmbeddingModel.get_model()

        if model == "fallback":
            return EmbeddingModel._fallback_encode(texts)

        return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    @staticmethod
    def _fallback_encode(texts: list[str]) -> np.ndarray:
        dim = 384
        embeddings = []
        for text in texts:
            embedding = np.zeros(dim)
            for i, char in enumerate(text):
                embedding[i % dim] += ord(char) / 256.0
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            embeddings.append(embedding)
        return np.array(embeddings)


@lru_cache(maxsize=1000)
def encode_single_text(text: str) -> tuple[float, ...]:
    model = EmbeddingModel.get_model()
    if model == "fallback":
        emb = EmbeddingModel._fallback_encode([text])[0]
    else:
        emb = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
    return tuple(emb.tolist())
