"""Recommendation engine combining BM25 + embeddings + personalization."""

import time
from typing import Optional
from loguru import logger

from src.models.dish import Dish
from src.models.user import UserProfile, UserPreference
from src.models.recommendation import Recommendation, RecommendationResponse
from src.services.dish_repository import DishRepository
from src.services.embedding_service import EmbeddingService
from src.services.similarity_engine import SimilarityEngine


class RecommendationEngine:
    """Main recommendation engine with hybrid retrieval."""

    def __init__(
        self,
        repository: DishRepository,
        embedding_service: EmbeddingService,
        similarity_engine: SimilarityEngine,
    ):
        self.repository = repository
        self.embedding_service = embedding_service
        self.similarity_engine = similarity_engine
        self.bm25_index: Optional[BM25Index] = None

    def initialize_bm25(self) -> None:
        """Build BM25 index over all dishes."""
        dishes = self.repository.get_all()
        texts = [d.get_search_text() for d in dishes]
        self.bm25_index = BM25Index(texts, dishes)
        logger.info(f"Built BM25 index with {len(dishes)} documents")

    def recommend(
        self,
        query: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
        similar_to: Optional[str] = None,
        max_results: int = 10,
        cuisine_filter: Optional[str] = None,
        min_spice: Optional[int] = None,
        max_spice: Optional[int] = None,
        vegetarian_only: bool = False,
        use_hybrid: bool = True,
    ) -> RecommendationResponse:
        """Generate personalized recommendations."""
        start_time = time.time()

        # Get candidates
        if similar_to:
            candidates = self._get_similarity_candidates(similar_to, max_results * 3)
            retrieval_method = "similarity"
        elif query:
            candidates = self._get_retrieval_candidates(query, max_results * 3, use_hybrid)
            retrieval_method = "hybrid" if use_hybrid else "bm25"
        else:
            candidates = self.repository.get_all()
            retrieval_method = "all"

        # Apply filters
        candidates = self._apply_filters(
            candidates, cuisine_filter, min_spice, max_spice, vegetarian_only
        )

        # Score and rank
        scored = self._score_candidates(candidates, query, user_profile, similar_to)
        ranked = sorted(scored, key=lambda x: x[1], reverse=True)[:max_results]

        # Build response
        recommendations = []
        for rank, (dish, score) in enumerate(ranked, start=1):
            rec = Recommendation(
                dish=dish,
                score=round(score, 4),
                rank=rank,
                match_reasons=self._generate_match_reasons(dish, query, user_profile),
                taste_map_coords=dish.taste_profile.to_taste_map_coords(),
            )
            recommendations.append(rec)

        processing_time = (time.time() - start_time) * 1000

        taste_map_data = [
            {
                "dish_id": r.dish.id,
                "name": r.dish.name,
                "x": r.taste_map_coords[0],
                "y": r.taste_map_coords[1],
                "spice_level": r.dish.taste_profile.spice_level,
                "cuisine": r.dish.cuisine,
            }
            for r in recommendations
        ]

        return RecommendationResponse(
            recommendations=recommendations,
            total_available=len(candidates),
            query=query,
            retrieval_method=retrieval_method,
            processing_time_ms=round(processing_time, 2),
            taste_map_data=taste_map_data,
        )

    def _get_similarity_candidates(self, dish_id: str, n: int) -> list[Dish]:
        similar = self.similarity_engine.find_similar_dishes(dish_id, top_k=n)
        return [dish for dish, _ in similar]

    def _get_retrieval_candidates(self, query: str, n: int, use_hybrid: bool) -> list[Dish]:
        if self.bm25_index is None:
            self.initialize_bm25()

        if use_hybrid:
            bm25_results = self.bm25_index.search(query, top_k=n)
            embed_results = self._embedding_search(query, top_k=n)
            # Merge with deduplication
            seen = set()
            merged = []
            for dish in bm25_results + embed_results:
                if dish.id not in seen:
                    seen.add(dish.id)
                    merged.append(dish)
            return merged
        return self.bm25_index.search(query, top_k=n)

    def _embedding_search(self, query: str, top_k: int) -> list[Dish]:
        query_embedding = self.embedding_service.encode_query(query)
        matrix = self.embedding_service.get_embedding_matrix()
        if matrix is None:
            return []

        similarities = matrix @ query_embedding
        top_indices = similarities.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            dish_id = self.embedding_service.get_dish_id_by_index(idx)
            if dish_id:
                dish = self.repository.get_by_id(dish_id)
                if dish:
                    results.append(dish)
        return results

    def _apply_filters(
        self,
        dishes: list[Dish],
        cuisine_filter: Optional[str] = None,
        min_spice: Optional[int] = None,
        max_spice: Optional[int] = None,
        vegetarian_only: bool = False,
    ) -> list[Dish]:
        results = dishes
        if cuisine_filter:
            results = [d for d in results if d.cuisine.lower() == cuisine_filter.lower()]
        if min_spice is not None:
            results = [d for d in results if d.taste_profile.spice_level >= min_spice]
        if max_spice is not None:
            results = [d for d in results if d.taste_profile.spice_level <= max_spice]
        if vegetarian_only:
            results = [d for d in results if d.is_vegetarian]
        return results

    def _score_candidates(
        self,
        candidates: list[Dish],
        query: Optional[str],
        user_profile: Optional[UserProfile],
        similar_to: Optional[str],
    ) -> list[tuple[Dish, float]]:
        scored = []
        for dish in candidates:
            base_score = self._get_base_score(dish, query, similar_to)
            pref_score = 0.0
            if user_profile:
                pref_score = self._compute_preference_score(dish, user_profile.preferences)
            total = 0.7 * base_score + 0.3 * pref_score
            scored.append((dish, total))
        return scored

    def _get_base_score(self, dish: Dish, query: Optional[str], similar_to: Optional[str]) -> float:
        if similar_to and self.bm25_index:
            similar = self.similarity_engine.find_similar_dishes(similar_to, top_k=50)
            for s_dish, sim_score in similar:
                if s_dish.id == dish.id:
                    return sim_score
            return 0.5
        if query and self.bm25_index:
            return self.bm25_index.score(dish.id, query)
        return 0.5

    def _compute_preference_score(self, dish: Dish, prefs: UserPreference) -> float:
        score = 0.0
        flavor_matches = len(set(dish.flavor_tags) & set(prefs.preferred_flavors))
        flavor_penalties = len(set(dish.flavor_tags) & set(prefs.disliked_flavors))
        score += 0.15 * flavor_matches - 0.2 * flavor_penalties

        texture_matches = len(set(dish.texture_tags) & set(prefs.preferred_textures))
        texture_penalties = len(set(dish.texture_tags) & set(prefs.disliked_textures))
        score += 0.1 * texture_matches - 0.15 * texture_penalties

        if prefs.preferred_cuisines and dish.cuisine in prefs.preferred_cuisines:
            score += 0.2
        if prefs.disliked_cuisines and dish.cuisine in prefs.disliked_cuisines:
            score -= 0.3

        spice_diff = abs(dish.taste_profile.spice_level - prefs.preferred_spice_level)
        score -= 0.05 * spice_diff

        return max(0.0, min(1.0, 0.5 + score))

    def _generate_match_reasons(
        self, dish: Dish, query: Optional[str], user_profile: Optional[UserProfile]
    ) -> list[str]:
        reasons = []
        if query:
            ql = query.lower()
            if "spicy" in ql and dish.taste_profile.spice_level >= 3:
                reasons.append(f"spicy (level {dish.taste_profile.spice_level}/5)")
            if "mild" in ql and dish.taste_profile.spice_level <= 2:
                reasons.append("mild dish")
            if "soft" in ql and "soft" in [t.value for t in dish.texture_tags]:
                reasons.append("soft texture")
            if "crispy" in ql and "crispy" in [t.value for t in dish.texture_tags]:
                reasons.append("crispy texture")

        if user_profile:
            prefs = user_profile.preferences
            if dish.cuisine in prefs.preferred_cuisines:
                reasons.append(f"you like {dish.cuisine}")
            flavor_overlap = set(dish.flavor_tags) & set(prefs.preferred_flavors)
            if flavor_overlap:
                reasons.append(f"flavors: {', '.join(flavor_overlap)}")

        if not reasons:
            reasons.append("matches your taste")
        return reasons[:3]


class BM25Index:
    """BM25 text search index."""

    def __init__(self, texts: list[str], dishes: list[Dish]):
        from rank_bm25 import BM25Okapi
        self.texts = texts
        self.dishes = dishes
        self.dish_id_map = {d.id: d for d in dishes}
        tokenized_texts = [t.lower().split() for t in texts]
        self.bm25 = BM25Okapi(tokenized_texts)
        self._score_cache: dict[str, dict[str, float]] = {}

    def search(self, query: str, top_k: int = 10) -> list[Dish]:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = scores.argsort()[::-1][:top_k]
        return [self.dishes[i] for i in top_indices if scores[i] > 0]

    def score(self, dish_id: str, query: str) -> float:
        cache_key = f"{dish_id}:{query}"
        if cache_key in self._score_cache:
            return self._score_cache[cache_key]

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        for i, dish in enumerate(self.dishes):
            if dish.id == dish_id:
                score = float(scores[i])
                self._score_cache[cache_key] = score
                return score
        return 0.0
