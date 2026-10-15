from copy import copy
from app.schemas.users import Preferences, MealIntent
from app.schemas.recipes import RecommendationRequest
from app.services.normalization import normalize
from app.services.recommendation import recommend

SAFETY_NOTE = "Bilinen alerjenler ve eksik içerik bilgisi ihtiyatla elenir. Ürün etiketlerini kontrol edin; Tencerem profesyonel tıbbi danışmanlık veya alerjen/çapraz bulaşma güvenliği garantisi sağlamaz."


def compatible(recipe, catalog, profile: Preferences, today_diet=None):
    ingredients = [catalog.registry.get(i.ingredient_id) for i in recipe.ingredients]
    if profile.allergies and any(not i.allergen_metadata_complete or set(i.allergens) & set(profile.allergies) for i in ingredients):
        return False
    for diet in (profile.dietary_pattern, today_diet):
        if diet not in (None,"standard") and any(not i.allergen_metadata_complete for i in ingredients): return False
        if diet == "vegetarian" and any(i.meat for i in ingredients): return False
        if diet == "vegan" and any(i.animal for i in ingredients): return False
        if diet == "pescatarian" and any(i.meat and i.category != "fish" for i in ingredients): return False
        if diet == "gluten_free" and any(i.gluten or not i.allergen_metadata_complete for i in ingredients): return False
        # Conservative milk exclusion; no lactose measurement is claimed.
        if diet == "lactose_free" and any("milk" in i.allergens or not i.allergen_metadata_complete for i in ingredients): return False
    return True


def personalized_recommend(catalog, profile: Preferences, intent: MealIntent, pantry):
    maximum = intent.max_minutes if intent.max_minutes is not None else profile.default_max_minutes or 30
    servings = intent.servings if intent.servings is not None else profile.default_servings
    safe = [r for r in catalog.recipes if compatible(r,catalog,profile,intent.dietary_pattern)]
    tokens = set(normalize(intent.craving).split())
    mentioned = {i.id for i in catalog.ingredients if any(set(normalize(a).split()) <= tokens for a in (i.name,*i.aliases))}
    compatible_ids = {i.ingredient_id for r in safe for i in r.ingredients}
    conflicts = []
    if mentioned - compatible_ids:
        conflicts.append("Aradığınız bir malzeme kayıtlı beslenme/alerji kısıtlarınızla uyuşmuyor veya içerik bilgisi eksik. Aramayı değiştirin; kalıcı tercihlerinizi Tercihlerim ekranında inceleyin.")
    eligible = [r for r in safe if intent.allow_disliked or not ({i.ingredient_id for i in r.ingredients} & set(profile.disliked_ingredients))]
    filtered = copy(catalog)
    filtered.recipes = tuple(eligible)
    useful = tuple(p for p in pantry if p.quantity is None or p.quantity > 0)
    names = ",".join(catalog.registry.get(p.ingredient_id).name for p in useful)
    result = recommend(filtered, RecommendationRequest(craving=intent.craving,servings=servings,
        max_prep_minutes=maximum,dietary_preference="none",pantry=names,limit=10), all_candidates=True)
    goals = set(profile.goals) | set(intent.temporary_tags)
    ranked = []
    for match in result.recipes:
        ids = {i.ingredient_id for i in match.recipe.ingredients}
        tags = {normalize(t) for t in match.recipe.tags}
        goal_hits = sum(["high_protein" in goals and "protein kaynagi" in tags,
            "quick" in goals and match.recipe.total_minutes <= 30,
            "economical" in goals and "ekonomik" in tags,
            "student_friendly" in goals and "ekonomik" in tags and match.recipe.total_minutes <= 30,
            "light" in goals and "hafif" in tags])
        likes = len(ids & set(profile.liked_ingredients))
        coverage = len(ids & {p.ingredient_id for p in useful})
        entry = match.model_dump(mode="json")
        entry["personalization_signals"] = {"pantry_matches":coverage,"liked_matches":likes,"goal_matches":goal_hits}
        entry["reasons"] += [f"Kayıtlı tercihler: {likes} sevilen malzeme, {goal_hits} hedef/etiket eşleşmesi. Hedefler klinik beslenme planı değildir."]
        ranked.append(((-coverage,-likes,-goal_hits,-match.score,match.recipe.total_minutes,match.recipe.slug),entry))
    ranked.sort(key=lambda row:row[0])
    data = result.model_dump(mode="json")
    data.update(recipes=[] if conflicts else [r for _,r in ranked[:5]], conflicts=conflicts,
        profile_applied=True, applied_servings=servings, applied_max_minutes=maximum,
        warnings=[SAFETY_NOTE,"Son kullanma tarihleri yalnızca kullanıcı bilgisidir; güvenlik veya tazelik güvencesi değildir.","Bütçe uygulanmaz; fiyat hesaplanmaz."],
        message=conflicts[0] if conflicts else "Kayıtlı tercihleriniz ve bugünkü seçiminizle eşleşen yemekler." if ranked else "Kısıtlarınıza uygun tarif bulunamadı. Aramayı veya süreyi değiştirin; alerji kısıtları gevşetilmez.")
    return data
