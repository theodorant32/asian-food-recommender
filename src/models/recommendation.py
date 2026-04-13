"""
Recommendation models for API requests and responses.

Defines the contract between the recommendation engine and the API layer.
"""

from typing import Optional
from pydantic import BaseModel, Field

from .dish import Dish


class RecommendationRequest(BaseModel):
    """
    Request model for getting recommendations.

    Supports multiple query types:
    - Text search: "something spicy like mapo tofu"
    - Preference-based: based on user profile
    - Similarity: "dishes similar to X"
    """
    query: Optional[str] = Field(None, description="Natural language query")
    user_profile: Optional[dict] = Field(None, description="User preferences")
    similar_to: Optional[str] = Field(None, description="Find dishes similar to this dish ID")

    # Filters
    max_results: int = Field(default=10, ge=1, le=50)
    cuisine_filter: Optional[str] = Field(None, description="Filter by cuisine")
    min_spice: Optional[int] = Field(None, ge=1, le=5)
    max_spice: Optional[int] = Field(None, ge=1, le=5)
    vegetarian_only: bool = False

    # Retrieval mode
    use_hybrid: bool = Field(
        default=True,
        description="Use hybrid retrieval (BM25 + embeddings)"
    )


class Recommendation(BaseModel):
    """
    A single recommendation with explanation.

    Includes reasoning so the UI can show "why this was recommended".
    """
    dish: Dish
    score: float = Field(..., description="Relevance score (higher = better match)")
    rank: int = Field(..., description="Ranking position")

    # Explanation fields
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Why this dish was recommended"
    )
    similarity_score: Optional[float] = Field(
        None,
        description="Similarity to query dish (if applicable)"
    )
    preference_match_score: Optional[float] = Field(
        None,
        description="How well it matches user preferences"
    )

    # Visual comparison data
    taste_map_coords: tuple[float, float] = Field(
        default=(0.5, 0.5),
        description="Coordinates for taste map visualization"
    )


class RecommendationResponse(BaseModel):
    """
    Complete response from the recommendation engine.
    """
    recommendations: list[Recommendation] = Field(
        ...,
        description="Ranked list of recommendations"
    )
    total_available: int = Field(
        ...,
        description="Total number of matching dishes"
    )
    query: Optional[str] = Field(None, description="Original query")

    # Metadata for debugging/evaluation
    retrieval_method: str = Field(
        default="hybrid",
        description="Method used: 'hybrid', 'bm25', 'embedding', 'collaborative'"
    )
    processing_time_ms: Optional[float] = Field(
        None,
        description="Time taken to generate recommendations"
    )

    # Taste map data for visualization
    taste_map_data: Optional[list[dict]] = Field(
        None,
        description="Dish coordinates for taste map display"
    )
