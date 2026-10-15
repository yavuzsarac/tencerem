from app.repositories.catalog import RecipeCatalog
from app.schemas.recipes import RecommendationRequest, RecommendationResponse, RecipeMatch
from app.services.normalization import normalize, normalize_pantry
from app.services.scaling import scale_recipe

# Ignore conversational fillers; no stemming, negation parsing or semantic inference.
STOP_WORDS = {"bir", "yemek", "istiyorum", "olsun", "ve", "ile", "icin", "canim", "bugun", "bana"}


def recommend(catalog: RecipeCatalog, preferences: RecommendationRequest, *, all_candidates: bool = False) -> RecommendationResponse:
    pantry = normalize_pantry(preferences.pantry, catalog.ingredients)
    pantry_ids = set(pantry.recognized)
    tokens = set(normalize(preferences.craving).split()) - STOP_WORDS
    # Exact token matches plus canonical ingredient aliases (tavuk -> chicken_breast).
    query_ingredients = {i.id for i in catalog.ingredients if any(
        set(normalize(alias).split()) <= tokens
        for alias in (i.name, *i.aliases))}
    matches = []
    for recipe in catalog.recipes:
        if recipe.total_minutes > preferences.max_prep_minutes:
            continue
        if preferences.dietary_preference != "none" and preferences.dietary_preference not in recipe.dietary_tags:
            continue
        name = set(normalize(recipe.name).split())
        category = set(normalize(recipe.category).split())
        tags = set(normalize(" ".join(recipe.tags)).split())
        ingredient_tokens = set(normalize(" ".join(i.name for i in recipe.ingredients)).split())
        ingredient_ids = {i.ingredient_id for i in recipe.ingredients}
        hits = {"name": tokens & name, "category": tokens & category, "tags": tokens & tags,
                "ingredients": tokens & ingredient_tokens}
        text_score = 10 * len(hits["name"]) + 6 * len(hits["category"]) + 4 * len(hits["tags"]) + 2 * len(hits["ingredients"]) + 2 * len(query_ingredients & ingredient_ids)
        # A specific query must have a positive textual match; never silently fall back.
        if tokens and not text_score:
            continue
        scaled = scale_recipe(recipe, preferences.servings)
        available = tuple(i for i in scaled.scaled_ingredients if i.ingredient_id in pantry_ids)
        missing = tuple(i for i in scaled.scaled_ingredients if i.ingredient_id not in pantry_ids)
        score = text_score + 3 * len(available)
        reasons = [f"Toplam {recipe.total_minutes} dakika; {preferences.max_prep_minutes} dakika sınırına uygun."]
        if text_score:
            reasons.append(f'“{preferences.craving}” aramanız ad, kategori, etiket veya malzemelerle eşleşti.')
        if preferences.dietary_preference != "none":
            reasons.append("Seçtiğiniz beslenme tercihine uygun içerik etiketleri var.")
        if available:
            reasons.append("Evde var olarak eşleşenler: " + ", ".join(i.name for i in available) + ".")
        matches.append(RecipeMatch(**scaled.model_dump(), available_ingredients=available,
            missing_ingredients=missing, score=score, reasons=tuple(reasons)))
    matches.sort(key=lambda m: (-m.score, m.recipe.total_minutes, m.recipe.slug))
    selected = tuple(matches if all_candidates else matches[:preferences.limit])
    return RecommendationResponse(requested_servings=preferences.servings, recipes=selected,
        normalized_pantry=pantry.normalized, recognized_pantry_ids=pantry.recognized, unrecognized_pantry=pantry.unrecognized,
        message="Kürasyonlu katalogdan eşleşen tarifler." if selected else "Bu tercihlere uygun tarif bulunamadı. Aramayı sadeleştirin veya toplam süre sınırını artırın.")
