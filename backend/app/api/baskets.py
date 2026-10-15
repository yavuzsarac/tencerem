from fastapi import APIRouter, Request
from app.schemas.baskets import BasketRequest, BasketPreview
from app.schemas.recipes import IngredientDefinition
from app.services.baskets import preview_basket

router = APIRouter(tags=["basket"])

@router.get("/ingredients", response_model=list[IngredientDefinition])
def list_ingredients(request: Request):
    return request.app.state.catalog.registry.ingredients

@router.post("/baskets/preview", response_model=BasketPreview)
def basket_preview(body: BasketRequest, request: Request):
    return preview_basket(request.app.state.catalog, body)
