"""Tests for data models."""

import pytest
from src.models.dish import Dish, TasteProfile, TextureTag, FlavorTag
from src.models.user import UserPreference, UserProfile, AdventureLevel
from src.models.recommendation import RecommendationRequest


class TestTasteProfile:
    def test_defaults(self):
        profile = TasteProfile()
        assert profile.spice_level == 2
        assert profile.richness == 3

    def test_bounds(self):
        with pytest.raises(Exception):
            TasteProfile(spice_level=0)
        with pytest.raises(Exception):
            TasteProfile(spice_level=6)

    def test_taste_map_coords(self):
        profile = TasteProfile(spice_level=5, richness=1)
        x, y = profile.to_taste_map_coords()
        assert x == 0.2
        assert y == 0.2


class TestDish:
    def test_minimal_dish(self):
        dish = Dish(id="test", name="Test Dish", cuisine="Chinese", description="A dish")
        assert dish.id == "test"
        assert dish.is_vegetarian is False

    def test_get_search_text(self):
        dish = Dish(
            id="test", name="Test", cuisine="Chinese", description="Delicious",
            flavor_tags=[FlavorTag.SPICY], texture_tags=[TextureTag.CRISPY],
            main_ingredients=["pork"],
        )
        text = dish.get_search_text()
        assert "Test" in text
        assert "spicy" in text
        assert "pork" in text

    def test_similarity_vector(self):
        dish = Dish(
            id="test", name="Test", cuisine="Test", description="Test",
            taste_profile=TasteProfile(spice_level=5, richness=3, complexity=2, texture_intensity=4),
            flavor_tags=[FlavorTag.SPICY, FlavorTag.UMAMI],
            texture_tags=[TextureTag.SOFT],
        )
        vec = dish.get_similarity_vector()
        assert len(vec) == 14
        assert vec[0] == 1.0


class TestUserPreference:
    def test_defaults(self):
        prefs = UserPreference()
        assert prefs.preferred_spice_level == 2
        assert prefs.is_vegetarian is False

    def test_matches_dietary(self):
        prefs = UserPreference(is_vegetarian=True)
        assert prefs.matches_dietary(True, False, False, False) is True
        assert prefs.matches_dietary(False, False, True, False) is False


class TestRecommendationRequest:
    def test_defaults(self):
        req = RecommendationRequest()
        assert req.max_results == 10
        assert req.use_hybrid is True

    def test_with_query(self):
        req = RecommendationRequest(query="spicy", max_results=20)
        assert req.query == "spicy"
        assert req.max_results == 20
