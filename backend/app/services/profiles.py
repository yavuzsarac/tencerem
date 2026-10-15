from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.users import UserPreferences, PantryEntry
from app.schemas.users import Preferences, PantryCreate
from app.schemas.baskets import PantryItem
from app.services.pantry import prepare_pantry


def read_preferences(db: Session, user_id: str) -> Preferences:
    record = db.get(UserPreferences, user_id)
    return Preferences(**{name:getattr(record,name) for name in Preferences.model_fields})


def save_preferences(db: Session, user_id: str, body: Preferences, registry) -> Preferences:
    for ident in (*body.liked_ingredients, *body.disliked_ingredients):
        if registry.get(ident) is None:
            raise HTTPException(422, "Sevilen/sevilmeyen malzemeleri kayıtlı malzeme listesinden seçin.")
    record = db.get(UserPreferences, user_id)
    for name, value in body.model_dump(mode="json").items():
        setattr(record, name, value)
    db.commit()
    return read_preferences(db, user_id)


def saved_pantry(db: Session, user_id: str) -> tuple[PantryItem, ...]:
    return tuple(PantryItem(ingredient_id=row.ingredient_id, quantity=row.quantity, unit=row.unit)
        for row in db.scalars(select(PantryEntry).where(PantryEntry.user_id==user_id).order_by(PantryEntry.ingredient_id)))


def overlay_pantry(saved: tuple[PantryItem,...], adjustments: tuple[PantryItem,...], registry):
    prepare_pantry(adjustments, registry)  # Reject accidental duplicate overrides.
    if len({i.ingredient_id for i in adjustments}) != len(adjustments):
        raise HTTPException(422, "Her geçici malzeme için tek stok düzeltmesi girin.")
    by_id = {i.ingredient_id:i for i in saved}
    by_id.update({i.ingredient_id:i for i in adjustments})
    return tuple(by_id[k] for k in sorted(by_id))
