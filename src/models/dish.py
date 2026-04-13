"""Dish data models with structured taste mapping."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TextureTag(str, Enum):
    """Texture descriptors for Asian dishes."""
    SILKY = "silky"
    SOFT = "soft"
    TENDER = "tender"
    CHEWY = "chewy"
    CRISPY = "crispy"
    CRUNCHY = "crunchy"
    FIRM = "firm"
    SLIMY = "slimy"
    FLUFFY = "fluffy"
    DENSE = "dense"
    MINCED = "minced"
    SHREDDED = "shredded"
    BROTHY = "brothy"
    CREAMY = "creamy"
    FATTY = "fatty"
    JUICY = "juicy"
    SMOOTH = "smooth"
    LIGHT = "light"
    VARIED = "varied"
    FRESH = "fresh"
    STICKY = "sticky"


class FlavorTag(str, Enum):
    """Flavor descriptors for Asian dishes."""
    SPICY = "spicy"
    SWEET = "sweet"
    SOUR = "sour"
    SALTY = "salty"
    UMAMI = "umami"
    BITTER = "bitter"
    NUMBING = "numbing"
    GARLICKY = "garlicky"
    GINGERY = "gingery"
    SMOKY = "smoky"
    EARTHY = "earthy"
    HERBAL = "herbal"
    CITRUSY = "citrusy"
    COCONUTTY = "coconutty"
    FERMENTED = "fermented"
    SAVORY = "savory"
    MILD = "mild"
    RICH = "rich"
    LIGHT = "light"
    FRESH = "fresh"
    NUTTY = "nutty"
    PEPPERY = "peppery"


class TasteProfile(BaseModel):
    """Taste characteristics for visual mapping and similarity."""
    spice_level: int = Field(default=2, ge=0, le=5)
    richness: int = Field(default=3, ge=1, le=5)
    complexity: int = Field(default=3, ge=1, le=5)
    texture_intensity: int = Field(default=3, ge=1, le=5)

    def to_taste_map_coords(self) -> tuple[float, float]:
        """Convert to 2D taste map (x: spicy->mild, y: light->rich)."""
        x = (6 - self.spice_level) / 5.0
        y = self.richness / 5.0
        return (x, y)


class Dish(BaseModel):
    """Asian dish with structured metadata."""
    id: str
    name: str
    cuisine: str
    region: Optional[str] = None
    description: str

    taste_profile: TasteProfile = Field(default_factory=TasteProfile)
    texture_tags: list[TextureTag] = Field(default_factory=list)
    flavor_tags: list[FlavorTag] = Field(default_factory=list)

    main_ingredients: list[str] = Field(default_factory=list)
    cooking_method: Optional[str] = None

    is_vegetarian: bool = False
    is_vegan: bool = False
    contains_meat: bool = True
    contains_seafood: bool = False

    image_url: Optional[str] = None
    image_color: str = "#E8A87C"
    embedding: Optional[list[float]] = None

    class Config:
        use_enum_values = True

    def get_search_text(self) -> str:
        """Generate searchable text for BM25."""
        parts = [
            self.name, self.cuisine, self.region or "",
            self.description,
            " ".join(self.flavor_tags),
            " ".join(self.texture_tags),
            " ".join(self.main_ingredients),
        ]
        return " ".join(filter(None, parts))

    def get_similarity_vector(self) -> list[float]:
        """Get numerical vector for similarity calculations."""
        base = [
            self.taste_profile.spice_level / 5.0,
            self.taste_profile.richness / 5.0,
            self.taste_profile.complexity / 5.0,
            self.taste_profile.texture_intensity / 5.0,
        ]
        flavor_encoding = [
            1.0 if FlavorTag.SPICY in self.flavor_tags else 0.0,
            1.0 if FlavorTag.UMAMI in self.flavor_tags else 0.0,
            1.0 if FlavorTag.SWEET in self.flavor_tags else 0.0,
            1.0 if FlavorTag.SOUR in self.flavor_tags else 0.0,
            1.0 if FlavorTag.NUMBING in self.flavor_tags else 0.0,
        ]
        texture_encoding = [
            1.0 if TextureTag.CRISPY in self.texture_tags else 0.0,
            1.0 if TextureTag.SOFT in self.texture_tags else 0.0,
            1.0 if TextureTag.CHEWY in self.texture_tags else 0.0,
            1.0 if TextureTag.SILKY in self.texture_tags else 0.0,
            1.0 if TextureTag.CRUNCHY in self.texture_tags else 0.0,
        ]
        return base + flavor_encoding + texture_encoding
