"""One owner-scoped saved-pantry basket path shared by preview and pricing."""
from fastapi import HTTPException
from app.schemas.baskets import BasketRequest
from app.services.baskets import preview_basket
from app.services.personalization import compatible
from app.services.profiles import read_preferences, saved_pantry, overlay_pantry


def saved_basket(catalog, db, user_id, request):
    profile = read_preferences(db,user_id)
    for selected in request.recipes:
        recipe = catalog.find(selected.slug)
        if recipe is not None and not compatible(recipe,catalog,profile):
            raise HTTPException(422, "Seçilen tarif kayıtlı beslenme/alerji kısıtlarınıza uymuyor veya içerik bilgisi eksik.")
    pantry = overlay_pantry(saved_pantry(db,user_id),request.pantry_adjustments,catalog.registry)
    return preview_basket(catalog,BasketRequest(recipes=request.recipes,pantry=pantry,optional_policy=request.optional_policy))
