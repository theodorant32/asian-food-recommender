"""Pytest fixtures."""

import pytest
import json


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


@pytest.fixture
def dish_repository(sample_dishes_data, tmp_path):
    data_file = tmp_path / "dishes.json"
    with open(data_file, "w") as f:
        json.dump(sample_dishes_data, f)
    from src.services.dish_repository import DishRepository
    repo = DishRepository(data_dir=str(tmp_path))
    repo.load()
    return repo
