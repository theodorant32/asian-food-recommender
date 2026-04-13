"""Embedding service using simple hash-based embeddings."""

import numpy as np
from loguru import logger

from src.models.dish import Dish
from src.services.dish_repository import DishRepository
from src.utils.embeddings import encode_texts


class EmbeddingService:
    """Generate and cache dish embeddings."""

    def __init__(self, repository: DishRepository):
        self.repository = repository
        self._embeddings: dict[str, np.ndarray] = {}
        self._embedding_matrix: np.ndarray | None = None
        self._dish_index: dict[int, str] = {}

    def compute_all_embeddings(self) -> np.ndarray:
        dishes = self.repository.get_all()
        texts = [d.get_search_text() for d in dishes]

        logger.info(f"Computing embeddings for {len(texts)} dishes...")
        embeddings = encode_texts(texts)

        self._embeddings = {}
        self._dish_index = {}
        for i, dish in enumerate(dishes):
            self._embeddings[dish.id] = embeddings[i]
            self._dish_index[i] = dish.id

        self._embedding_matrix = embeddings
        logger.info(f"Embedding matrix: {embeddings.shape}")
        return embeddings

    def get_embedding(self, dish_id: str) -> np.ndarray | None:
        if not self._embeddings:
            self.compute_all_embeddings()
        return self._embeddings.get(dish_id)

    def get_embedding_matrix(self) -> np.ndarray:
        if self._embedding_matrix is None:
            self.compute_all_embeddings()
        return self._embedding_matrix

    def get_dish_id_by_index(self, index: int) -> str | None:
        return self._dish_index.get(index)

    def encode_query(self, query: str) -> np.ndarray:
        embeddings = encode_texts([query])
        return embeddings[0]
