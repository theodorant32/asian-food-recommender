"""Simple text similarity without heavy ML dependencies."""

import hashlib
import numpy as np


def encode_text(text: str, dim: int = 128) -> np.ndarray:
    """Create a simple hash-based embedding for text."""
    embedding = np.zeros(dim)
    for i, char in enumerate(text.lower()):
        embedding[i % dim] += ord(char) / 256.0
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


def encode_texts(texts: list[str], dim: int = 128) -> np.ndarray:
    """Encode multiple texts."""
    return np.array([encode_text(t, dim) for t in texts])
