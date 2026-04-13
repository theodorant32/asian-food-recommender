#!/usr/bin/env python3
"""
Data validation script.

Ensures dish data is well-formed before deployment.
"""

import json
import sys
from pathlib import Path


def validate_dishes(data_file: str) -> tuple[bool, list[str]]:
    """
    Validate dish data file.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    path = Path(data_file)

    if not path.exists():
        return False, [f"Data file not found: {data_file}"]

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]

    if "dishes" not in data:
        return False, ["Missing 'dishes' key in data file"]

    dishes = data["dishes"]
    if not isinstance(dishes, list):
        return False, ["'dishes' must be a list"]

    if len(dishes) == 0:
        errors.append("Warning: No dishes in data file")

    required_fields = ["id", "name", "cuisine", "description"]
    optional_fields = [
        "region", "taste_profile", "texture_tags", "flavor_tags",
        "main_ingredients", "cooking_method", "is_vegetarian", "is_vegan",
        "contains_meat", "contains_seafood", "image_url", "image_color"
    ]

    valid_spice_range = range(1, 6)
    valid_richness_range = range(1, 6)
    valid_complexity_range = range(1, 6)
    valid_texture_range = range(1, 6)

    seen_ids = set()

    for i, dish in enumerate(dishes):
        prefix = f"Dish[{i}] ({dish.get('id', 'unknown')})"

        # Check required fields
        for field in required_fields:
            if field not in dish:
                errors.append(f"{prefix}: Missing required field '{field}'")

        # Check ID uniqueness
        dish_id = dish.get("id")
        if dish_id:
            if dish_id in seen_ids:
                errors.append(f"{prefix}: Duplicate ID '{dish_id}'")
            seen_ids.add(dish_id)

        # Check taste_profile bounds
        taste = dish.get("taste_profile", {})
        if taste:
            spice = taste.get("spice_level", 0)
            if spice not in valid_spice_range:
                errors.append(f"{prefix}: spice_level {spice} out of range [1-5]")

            richness = taste.get("richness", 0)
            if richness not in valid_richness_range:
                errors.append(f"{prefix}: richness {richness} out of range [1-5]")

            complexity = taste.get("complexity", 0)
            if complexity not in valid_complexity_range:
                errors.append(f"{prefix}: complexity {complexity} out of range [1-5]")

            texture = taste.get("texture_intensity", 0)
            if texture not in valid_texture_range:
                errors.append(f"{prefix}: texture_intensity {texture} out of range [1-5]")

    is_valid = len(errors) == 0 or all(e.startswith("Warning:") for e in errors)
    return is_valid, errors


def main():
    default_data_file = Path(__file__).parent.parent / "data" / "dishes.json"

    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = str(default_data_file)

    print(f"Validating: {data_file}")
    print("-" * 50)

    is_valid, errors = validate_dishes(data_file)

    if errors:
        print(f"\nFound {len(errors)} issue(s):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ All validations passed!")

    # Summary
    with open(data_file, "r") as f:
        data = json.load(f)
    print(f"\nSummary: {len(data.get('dishes', []))} dishes loaded")

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
