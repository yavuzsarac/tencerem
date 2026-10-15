from fastapi import APIRouter, HTTPException, Query, Request
from app.schemas.recipes import Recipe, RecommendationRequest, RecommendationResponse, ScaledRecipe
from app.services.recommendation import recommend
from app.services.scaling import scale_recipe

router = APIRouter(prefix="/recipes", tags=["recipes"])

@router.get("", response_model=list[Recipe])
def list_recipes(request: Request):
    return request.app.state.catalog.recipes

@router.post("/recommend", response_model=RecommendationResponse)
def recommend_recipes(preferences: RecommendationRequest, request: Request):
    return recommend(request.app.state.catalog, preferences)

@router.get("/{slug}", response_model=ScaledRecipe)
def recipe_detail(slug: str, request: Request, servings: int | None = Query(default=None, ge=1, le=12)):
    recipe = request.app.state.catalog.find(slug)
    if recipe is None:
        raise HTTPException(404, detail="Tarif bulunamadı. Tarif listesinden geçerli bir tarif seçin.")
    return scale_recipe(recipe, servings if servings is not None else recipe.base_servings)
