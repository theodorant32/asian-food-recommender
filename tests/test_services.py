"""Tests for service layer."""

import pytest
import json
from src.services.dish_repository import DishRepository


@pytest.fixture
def dish_repository(sample_dishes_data, tmp_path):
    data_file = tmp_path / "dishes.json"
    with open(data_file, "w") as f:
        json.dump(sample_dishes_data, f)
    repo = DishRepository(data_dir=str(tmp_path))
    repo.load()
    return repo


@pytest.fixture
def sample_dishes_data():
    return {
        "dishes": [
            {
                "id": "dish1", "name": "Dish One", "cuisine": "Chinese",
                "description": "Test dish", "taste_profile": {"spice_level": 3, "richness": 3, "complexity": 3, "texture_intensity": 3},
                "texture_tags": ["soft"], "flavor_tags": ["umami"], "main_ingredients": ["tofu"],
                "is_vegetarian": True, "contains_meat": False, "contains_seafood": False,
            },
            {
                "id": "dish2", "name": "Dish Two", "cuisine": "Japanese",
                "description": "Another dish", "taste_profile": {"spice_level": 1, "richness": 2, "complexity": 2, "texture_intensity": 2},
                "texture_tags": ["crispy"], "flavor_tags": ["mild"], "main_ingredients": ["fish"],
                "is_vegetarian": False, "contains_meat": False, "contains_seafood": True,
            },
        ]
    }


class TestDishRepository:
    def test_load_dishes(self, dish_repository):
        assert dish_repository.count() == 2

    def test_get_by_id(self, dish_repository):
        dish = dish_repository.get_by_id("dish1")
        assert dish.name == "Dish One"

    def test_get_by_id_not_found(self, dish_repository):
        dish = dish_repository.get_by_id("nonexistent")
        assert dish is None

    def test_get_by_cuisine(self, dish_repository):
        chinese = dish_repository.get_by_cuisine("Chinese")
        assert len(chinese) == 1

    def test_search_by_name(self, dish_repository):
        results = dish_repository.search_by_name("one")
        assert len(results) == 1

    def test_get_cuisines(self, dish_repository):
        cuisines = dish_repository.get_available_cuisines()
        assert "Chinese" in cuisines
        assert "Japanese" in cuisines
