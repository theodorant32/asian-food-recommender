"""Repository for loading and managing dish data."""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

from src.models.dish import Dish, TasteProfile


class DishRepository:
    """Data access layer for dishes."""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.dishes: dict[str, Dish] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        dishes_file = self.data_dir / "dishes.json"
        if not dishes_file.exists():
            raise FileNotFoundError(f"Dish data not found at {dishes_file}")

        with open(dishes_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for dish_data in data.get("dishes", []):
            taste_profile = TasteProfile(**dish_data.pop("taste_profile", {}))
            dish = Dish(**dish_data, taste_profile=taste_profile)
            self.dishes[dish.id] = dish

        self._loaded = True
        logger.info(f"Loaded {len(self.dishes)} dishes")

    def get_all(self) -> list[Dish]:
        if not self._loaded:
            self.load()
        return list(self.dishes.values())

    def get_by_id(self, dish_id: str) -> Optional[Dish]:
        if not self._loaded:
            self.load()
        return self.dishes.get(dish_id)

    def get_by_cuisine(self, cuisine: str) -> list[Dish]:
        if not self._loaded:
            self.load()
        return [d for d in self.dishes.values() if d.cuisine.lower() == cuisine.lower()]

    def get_by_ids(self, dish_ids: list[str]) -> list[Dish]:
        if not self._loaded:
            self.load()
        return [self.dishes[did] for did in dish_ids if did in self.dishes]

    def search_by_name(self, query: str) -> list[Dish]:
        if not self._loaded:
            self.load()
        query_lower = query.lower()
        return [d for d in self.dishes.values() if query_lower in d.name.lower()]

    def get_available_cuisines(self) -> list[str]:
        if not self._loaded:
            self.load()
        return sorted(set(d.cuisine for d in self.dishes.values()))

    def count(self) -> int:
        return len(self.dishes)
