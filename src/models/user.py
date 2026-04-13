"""
User preference models for personalization.

Captures taste preferences, dietary restrictions, and adventure level
to power personalized recommendations.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AdventureLevel(str, Enum):
    """How willing the user is to try unfamiliar dishes."""
    CAUTIOUS = "cautious"      # Stick to familiar, mild dishes
    MODERATE = "moderate"      # Open to some new experiences
    ADVENTUROUS = "adventurous"  # Willing to try anything


class UserPreference(BaseModel):
    """
    A user's taste preferences.

    Used to score and rank recommendations based on personal taste.
    """
    # Flavor preferences (positive = likes, negative = dislikes)
    preferred_flavors: list[str] = Field(
        default_factory=list,
        description="Flavors the user enjoys (e.g., ['spicy', 'umami'])"
    )
    disliked_flavors: list[str] = Field(
        default_factory=list,
        description="Flavors the user avoids"
    )

    # Texture preferences
    preferred_textures: list[str] = Field(
        default_factory=list,
        description="Textures the user enjoys (e.g., ['crispy', 'silky'])"
    )
    disliked_textures: list[str] = Field(
        default_factory=list,
        description="Textures the user avoids"
    )

    # Cuisine preferences
    preferred_cuisines: list[str] = Field(
        default_factory=list,
        description="Preferred cuisine types (e.g., ['Chinese', 'Japanese'])"
    )
    disliked_cuisines: list[str] = Field(
        default_factory=list,
        description="Cuisines the user avoids"
    )

    # Spice preference
    preferred_spice_level: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Ideal spice level (1=mild, 5=very spicy)"
    )

    # Dietary restrictions
    is_vegetarian: bool = False
    is_vegan: bool = False
    no_pork: bool = False
    no_beef: bool = False
    no_seafood: bool = False

    # Adventure level affects recommendation diversity
    adventure_level: AdventureLevel = AdventureLevel.MODERATE

    def matches_dietary(self, dish_is_vegetarian: bool, dish_is_vegan: bool,
                        contains_meat: bool, contains_seafood: bool) -> bool:
        """Check if a dish meets dietary restrictions."""
        if self.is_vegan and not dish_is_vegan:
            return False
        if self.is_vegetarian and not dish_is_vegetarian:
            return False
        if self.no_pork and "pork" in str(contains_meat).lower():
            return False
        if self.no_beef and "beef" in str(contains_meat).lower():
            return False
        if self.no_seafood and contains_seafood:
            return False
        return True


class UserProfile(BaseModel):
    """
    Complete user profile combining preferences and history.

    This is what the recommendation engine uses to personalize results.
    """
    user_id: Optional[str] = None
    name: Optional[str] = None

    preferences: UserPreference = Field(default_factory=UserPreference)

    # Interaction history (for future ML improvements)
    liked_dishes: list[str] = Field(
        default_factory=list,
        description="List of dish IDs the user liked"
    )
    disliked_dishes: list[str] = Field(
        default_factory=list,
        description="List of dish IDs the user disliked"
    )
    viewed_dishes: list[str] = Field(
        default_factory=list,
        description="List of dish IDs the user viewed"
    )

    # Computed: embedding of user's taste for similarity search
    taste_embedding: Optional[list[float]] = None

    def get_preference_summary(self) -> dict:
        """Get a human-readable summary of preferences."""
        return {
            "likes": self.preferences.preferred_flavors + self.preferences.preferred_textures,
            "dislikes": self.preferences.disliked_flavors + self.preferences.disliked_textures,
            "cuisines": self.preferences.preferred_cuisines,
            "spice_level": self.preferences.preferred_spice_level,
            "adventure": self.preferences.adventure_level.value,
        }
