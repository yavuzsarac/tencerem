import re
import unicodedata
from dataclasses import dataclass
from app.schemas.recipes import IngredientDefinition


def normalize(value: str) -> str:
    value = value.translate(str.maketrans({"I": "ı", "İ": "i"})).lower().replace("ı", "i")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))

@dataclass(frozen=True)
class Pantry:
    normalized: tuple[str, ...]
    recognized: tuple[str, ...]
    unrecognized: tuple[str, ...]


def normalize_pantry(value: str, ingredients: tuple[IngredientDefinition, ...]) -> Pantry:
    # Local import avoids a module cycle; both paths use the canonical registry.
    from app.repositories.ingredients import IngredientRegistry
    registry = IngredientRegistry(ingredients)
    entries = tuple(dict.fromkeys(filter(None, (normalize(v) for v in value.split(",")))))
    recognized = tuple(dict.fromkeys(registry.resolve(v) for v in entries if registry.resolve(v) is not None))
    return Pantry(entries, recognized, tuple(v for v in entries if registry.resolve(v) is None))
