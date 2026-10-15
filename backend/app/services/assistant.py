"""Hybrid decisions: untrusted intent -> deterministic candidates -> validated choice."""
from copy import copy
import re
from app.schemas.assistant import ParsedIntent, Decision, SessionIntent, AssistantResponse
from app.schemas.baskets import PantryItem
from app.schemas.users import MealIntent, Preferences
from app.services.ai_provider import invoke
from app.services.normalization import normalize, normalize_pantry
from app.services.personalization import personalized_recommend, compatible
from app.services.profiles import overlay_pantry

FALLBACK_NOTICE = "Yapay zekâ desteği kullanılamıyor; sınırlı Türkçe kuralları ve kayıtlı katalogla öneri hazırlanıyor. Anlaşılan tercihleri kontrol edin."


def local_parse(text, catalog):
    """Small, explicitly limited offline interpreter; never presented as AI."""
    value = normalize(text)
    includes, excludes, pantry = [], [], []
    for ingredient in catalog.ingredients:
        aliases = sorted((normalize(a) for a in (ingredient.name, *ingredient.aliases)), key=len, reverse=True)
        for alias in aliases:
            # Small Turkish suffix allowlist, no aggressive fuzzy matching.
            found = re.search(r"\b" + re.escape(alias) + r"(?:li|lu|siz|suz)?\b", value)
            if not found: continue
            tail = value[found.end():found.end()+30]
            before = value[max(0, found.start()-30):found.start()]
            negative = bool(re.match(r"\s+(?:istemiyorum|olmasin|yemek istemiyorum|yedim)", tail)) or found.group().endswith(("siz", "suz"))
            if negative: excludes.append(ingredient.id)
            elif "evde" in before and re.match(r"\s+var\b", tail): pantry.append(ingredient.id)
            else: includes.append(ingredient.id)
            break
    minutes = re.search(r"\b(\d+)\s*(?:dakika(?:da|dan)?|dk)\b", value)
    servings = re.search(r"\b(\d+)\s*kisi(?:lik|yiz)?\b", value)
    goals = []
    for words, goal in ((('protein', 'proteinli'), 'high_protein'), (('hizli', 'ugrasmak istemiyorum'), 'quick'),
                        (('ucuz', 'param az', 'ekonomik'), 'economical'), (('ogrenci',), 'student_friendly'), (('hafif',), 'light')):
        if any(word in value for word in words): goals.append(goal)
    unsupported = []
    if re.search(r"\b(?:tencere|tava|firin)(?:da|de)?\b", value):
        unsupported.append("Ekipman kısıtı katalogda doğrulanamıyor.")
    if (minutes and not 5 <= int(minutes[1]) <= 240) or (servings and not 1 <= int(servings[1]) <= 12):
        unsupported.append("Süre 5–240 dakika, kişi sayısı 1–12 olmalı.")
    scope = bool(includes or excludes or pantry or goals or minutes or servings or
                 re.search(r"\b(yemek|yesem|yiyecegimi|oner|baska|etsiz|vejetaryen|vegan|kahvalti|corba|salata)\b", value))
    diet = "vegan" if "vegan" in value else "vegetarian" if any(w in value for w in ("etsiz", "vejetaryen")) else None
    return ParsedIntent(in_scope=scope, servings=int(servings[1]) if servings and 1 <= int(servings[1]) <= 12 else None,
        max_minutes=int(minutes[1]) if minutes and 5 <= int(minutes[1]) <= 240 else 20 if "daha hizli" in value else 30 if "quick" in goals else None,
        dietary_pattern=diet, goals=tuple(goals), include_ingredients=tuple(includes),
        exclude_ingredients=tuple(excludes), pantry_ingredients=tuple(pantry), unsupported_constraints=tuple(unsupported))


def resolve_names(names, registry):
    resolved, unknown = [], []
    for name in names:
        ident = name if registry.get(name) else registry.resolve(name)
        if ident: resolved.append(ident)
        else: unknown.append(name)
    return tuple(dict.fromkeys(resolved)), unknown


async def decide(catalog, settings, provider, request, profile=None, saved=()):
    authenticated = profile is not None
    profile = profile or Preferences()
    previous = request.previous_intent or SessionIntent()
    # Revalidate client-provided state and canonical IDs; it conveys no authority.
    for ident in (*previous.include_ids, *previous.exclude_ids, *previous.pantry_ids):
        if catalog.registry.get(ident) is None:
            from fastapi import HTTPException
            raise HTTPException(422, "Önceki seçimde bilinmeyen malzeme var. Yeni bir karar başlatın.")
    notices = []
    local = local_parse(request.text, catalog)
    parsed = local
    used_ai = False
    if provider is not None:
        try:
            async def parse():
                context = previous.model_dump(mode="json")
                context["meal"].pop("pantry_adjustments", None)
                context["meal"].pop("max_budget_try", None)
                return ParsedIntent.model_validate(await provider.parse_meal_intent(request.text, context))
            parsed = await invoke(settings, "parse", parse)
            used_ai = True
        except Exception:
            notices.append(FALLBACK_NOTICE)
    else: notices.append(FALLBACK_NOTICE)
    # Offline-recognized explicit negatives also bind the model path.
    include, unknown_include = resolve_names(parsed.include_ingredients, catalog.registry)
    exclude, unknown_exclude = resolve_names(parsed.exclude_ingredients, catalog.registry)
    declared, unknown_pantry = resolve_names(parsed.pantry_ingredients, catalog.registry)
    include_local, _ = resolve_names(local.include_ingredients, catalog.registry)
    exclude_local, _ = resolve_names(local.exclude_ingredients, catalog.registry)
    declared_local, _ = resolve_names(local.pantry_ingredients, catalog.registry)
    exclusions = tuple(dict.fromkeys((*previous.exclude_ids, *exclude, *exclude_local)))
    included = tuple(i for i in dict.fromkeys((*previous.include_ids, *include, *include_local)) if i not in exclusions)
    patch = {key: value for key, value in {"servings": parsed.servings, "max_minutes": parsed.max_minutes,
             "dietary_pattern": parsed.dietary_pattern}.items() if value is not None}
    # Numbers/diet explicitly understood locally cannot be removed by a model.
    for key in ("servings", "max_minutes", "dietary_pattern"):
        if getattr(local, key) is not None: patch[key] = getattr(local, key)
    patch["temporary_tags"] = tuple(dict.fromkeys((*previous.meal.temporary_tags, *parsed.goals, *local.goals)))
    if "daha hizli" in normalize(request.text) and request.current_slug:
        current = catalog.find(request.current_slug)
        if current:
            patch["max_minutes"] = max(5, current.total_minutes - 1)
    meal = previous.meal.model_copy(update=patch)
    # Structured controls are explicit user choices, not inferred model preferences.
    control_patch = request.controls.model_dump(exclude_unset=True)
    if "temporary_tags" in control_patch:
        control_patch["temporary_tags"] = tuple(dict.fromkeys((*meal.temporary_tags, *control_patch["temporary_tags"])))
    meal = MealIntent.model_validate({**meal.model_dump(), **control_patch, "craving": "yemek"})
    remembered_pantry = tuple(dict.fromkeys((*previous.pantry_ids, *declared, *declared_local)))
    intent = SessionIntent(meal=meal, include_ids=included, exclude_ids=exclusions, pantry_ids=remembered_pantry)
    named = normalize_pantry(request.pantry, catalog.ingredients)
    pantry = overlay_pantry(saved, tuple(PantryItem(ingredient_id=i) for i in named.recognized), catalog.registry)
    pantry = overlay_pantry(pantry, tuple(PantryItem(ingredient_id=i) for i in remembered_pantry if i not in {p.ingredient_id for p in pantry}), catalog.registry)
    pantry = overlay_pantry(pantry, meal.pantry_adjustments, catalog.registry)
    restricted = copy(catalog)
    restricted.recipes = tuple(r for r in catalog.recipes if not ({i.ingredient_id for i in r.ingredients} & set(exclusions))
        and set(included) <= {i.ingredient_id for i in r.ingredients})
    conflicts = []
    safe_ids = {i.ingredient_id for r in catalog.recipes if compatible(r, catalog, profile, meal.dietary_pattern) for i in r.ingredients}
    if set(included) - safe_ids:
        conflicts.append("İstenen malzeme kayıtlı beslenme veya alerji kısıtlarınla uyuşmuyor. Başka bir malzeme seç; güvenlik kısıtları korunur.")
    unknown = unknown_include + unknown_exclude
    if unknown: conflicts.append("Bir malzeme güvenle eşleştirilemedi. Kayıtlı malzeme adıyla tekrar dene.")
    if unknown_pantry or named.unrecognized: notices.append("Bazı ev malzemeleri eşleştirilemedi; stok varsayılmadı.")
    unsupported = tuple(dict.fromkeys((*parsed.unsupported_constraints, *local.unsupported_constraints)))
    if unsupported: conflicts.append("Bu istek katalog bilgisiyle doğrulanamıyor. Ekipman veya diğer özel koşulları değiştirerek tekrar dene.")
    if not parsed.in_scope or (not used_ai and not local.in_scope):
        conflicts.append("Yalnızca yemek seçimine yardımcı olabilirim. Ne yemek istediğini veya süreni yaz.")
    data = personalized_recommend(restricted, profile, meal, pantry, max_results=24)
    candidates = data["recipes"]
    unseen = [entry for entry in candidates if entry["recipe"]["slug"] not in request.shown_slugs]
    if candidates and not unseen:
        notices.append("Uygun alternatiflerin hepsi gösterildi; seçenekler yeniden başlıyor.")
    candidates = (unseen or candidates)[:5]
    selected = candidates[0] if candidates and not conflicts else None
    if selected and provider is not None and used_ai:
        compact = [{"slug": c["recipe"]["slug"], "name": c["recipe"]["name"],
                    "minutes": c["recipe"]["total_minutes"], "signals": c["personalization_signals"]} for c in candidates]
        try:
            async def choose():
                context = intent.model_dump(mode="json")
                context["meal"].pop("pantry_adjustments", None)
                context["meal"].pop("max_budget_try", None)
                decision = Decision.model_validate(await provider.choose_candidate(context, compact))
                if decision.slug not in {c["slug"] for c in compact}: raise ValueError("Outside allowed set")
                return decision
            decision = await invoke(settings, "choose", choose)
            selected = next(c for c in candidates if c["recipe"]["slug"] == decision.slug)
        except Exception:
            used_ai = False
            notices.append("Karar desteği yanıtı doğrulanamadı; güvenli katalog sıralaması kullanıldı.")
    needs = []
    if selected:
        signals = selected["personalization_signals"]
        needs.append(f"Katalogdaki toplam süre {selected['recipe']['total_minutes']} dakika; süre sınırına uygun.")
        if signals["pantry_matches"]: needs.append("Evde var olarak bildirdiğin malzemelerle eşleşiyor; miktar yeterliliği sepette hesaplanır.")
        if signals["goal_matches"]: needs.append("Seçili hedeflerinle katalog etiketleri eşleşiyor; besin değeri hesaplanmadı.")
        if signals["liked_matches"]: needs.append("Kayıtlı sevdiğin malzemelerle eşleşiyor.")
    data["recipes"] = [selected] if selected else []
    data["conflicts"] = conflicts
    if conflicts: data["message"] = conflicts[0]
    elif not selected: data["message"] = "Bu koşullara uygun tarif bulunamadı. Süreyi veya bugünkü isteğini değiştir; güvenlik kısıtları korunur."
    data["profile_applied"] = authenticated
    return AssistantResponse(intent=intent, recommendations=data,
        engine="ai_assisted" if used_ai else "deterministic_fallback", notices=tuple(dict.fromkeys(notices)),
        selected_slug=selected["recipe"]["slug"] if selected else None,
        reason=" ".join(needs) if selected else None, matched_needs=tuple(needs),
        understood=tuple([*("İstenen: " + catalog.registry.get(i).name for i in included),
                          *("Hariç: " + catalog.registry.get(i).name for i in exclusions),
                          *("Evde var bildirildi: " + catalog.registry.get(i).name for i in remembered_pantry)]),
        tradeoffs=("Katalog süreleri tahminidir. Fiyat ve besin değeri hesabı yapılmaz.",))
