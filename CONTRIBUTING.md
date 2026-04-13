## Adding a Dish

Edit `data/dishes.json`. Minimum required:

```json
{
  "id": "unique_slug",
  "name": "Dish Name",
  "cuisine": "Cuisine",
  "description": "What is it?",
  "taste_profile": {"spice_level": 3, "richness": 3, "complexity": 3, "texture_intensity": 3},
  "texture_tags": ["soft"],
  "flavor_tags": ["umami"],
  "main_ingredients": ["ingredient"],
  "is_vegetarian": false,
  "contains_meat": true,
  "contains_seafood": false
}
```

Validate with: `python scripts/validate_data.py`
