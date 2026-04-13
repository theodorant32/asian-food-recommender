"""Food similarity engine."""

import numpy as np
from loguru import logger

from src.models.dish import Dish
from src.services.dish_repository import DishRepository
from src.services.embedding_service import EmbeddingService


class SimilarityEngine:
    """Compute dish similarity using embeddings and features."""

    def __init__(self, repository: DishRepository, embedding_service: EmbeddingService):
        self.repository = repository
        self.embedding_service = embedding_service

    def find_similar_dishes(
        self, dish_id: str, top_k: int = 10, method: str = "hybrid"
    ) -> list[tuple[Dish, float]]:
        source_dish = self.repository.get_by_id(dish_id)
        if not source_dish:
            logger.error(f"Dish not found: {dish_id}")
            return []

        if method == "embedding":
            scores = self._similarity_by_embedding(source_dish)
        elif method == "feature":
            scores = self._similarity_by_features(source_dish)
        else:
            scores = self._similarity_hybrid(source_dish)

        results = sorted(scores, key=lambda x: x[1], reverse=True)
        return [(d, s) for d, s in results if d.id != dish_id][:top_k]

    def _similarity_by_embedding(self, dish: Dish) -> list[tuple[Dish, float]]:
        matrix = self.embedding_service.get_embedding_matrix()
        dish_embedding = self.embedding_service.get_embedding(dish.id)
        if dish_embedding is None or matrix is None:
            return []

        similarities = matrix @ dish_embedding
        results = []
        for i, score in enumerate(similarities):
            dish_id = self.embedding_service.get_dish_id_by_index(i)
            if dish_id:
                d = self.repository.get_by_id(dish_id)
                if d:
                    results.append((d, float(score)))
        return results

    def _similarity_by_features(self, dish: Dish) -> list[tuple[Dish, float]]:
        results = []
        for other in self.repository.get_all():
            score = self._compute_feature_similarity(dish, other)
            results.append((other, score))
        return results

    def _compute_feature_similarity(self, d1: Dish, d2: Dish) -> float:
        taste_diff = [
            d1.taste_profile.spice_level - d2.taste_profile.spice_level,
            d1.taste_profile.richness - d2.taste_profile.richness,
            d1.taste_profile.complexity - d2.taste_profile.complexity,
            d1.taste_profile.texture_intensity - d2.taste_profile.texture_intensity,
        ]
        taste_distance = np.sqrt(np.sum(np.array(taste_diff) ** 2))
        taste_similarity = 1.0 / (1.0 + taste_distance / 4.0)

        flavor_sim = self._jaccard_similarity(set(d1.flavor_tags), set(d2.flavor_tags))
        texture_sim = self._jaccard_similarity(set(d1.texture_tags), set(d2.texture_tags))
        cuisine_bonus = 0.2 if d1.cuisine == d2.cuisine else 0.0

        return min(0.35 * taste_similarity + 0.25 * flavor_sim + 0.20 * texture_sim + 0.20 * cuisine_bonus + 0.2, 1.0)

    def _similarity_hybrid(self, dish: Dish) -> list[tuple[Dish, float]]:
        emb_results = self._similarity_by_embedding(dish)
        feat_results = self._similarity_by_features(dish)

        emb_scores = {r[0].id: r[1] for r in emb_results}
        feat_scores = {r[0].id: r[1] for r in feat_results}

        emb_max = max(emb_scores.values()) if emb_scores else 1.0
        feat_max = max(feat_scores.values()) if feat_scores else 1.0

        results = []
        for d in self.repository.get_all():
            emb_score = emb_scores.get(d.id, 0) / emb_max if emb_max else 0
            feat_score = feat_scores.get(d.id, 0) / feat_max if feat_max else 0
            results.append((d, 0.6 * emb_score + 0.4 * feat_score))
        return results

    @staticmethod
    def _jaccard_similarity(set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        return len(set1 & set2) / len(set1 | set2) if len(set1 | set2) > 0 else 0.0
