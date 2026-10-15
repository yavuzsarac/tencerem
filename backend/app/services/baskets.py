from collections import defaultdict
from decimal import Decimal, localcontext
from app.repositories.catalog import RecipeCatalog
from app.schemas.baskets import (BasketRequest, BasketPreview, BasketItem, BasketSummary,
    QuantityComponent, RecipeContribution, SelectedRecipe, PantryStock)
from app.schemas.recipes import Unit, UNIT_LABELS
from app.services.pantry import prepare_pantry, BasketInputError
from app.services.quantities import normalize_quantity, display_quantity
from app.services.scaling import scale_recipe


def preview_basket(catalog: RecipeCatalog, request: BasketRequest) -> BasketPreview:
    # Bounded inputs fit within this precision; isolate arithmetic from caller context.
    with localcontext() as context:
        context.prec = 28
        return _calculate(catalog, request)


def _calculate(catalog: RecipeCatalog, request: BasketRequest) -> BasketPreview:
    pantry = prepare_pantry(request.pantry, catalog.registry)
    groups: dict[str, dict[Unit, list[RecipeContribution]]] = defaultdict(lambda: defaultdict(list))
    selected = []
    excluded = 0
    for index, selection in enumerate(request.recipes):
        recipe = catalog.find(selection.slug)
        if recipe is None:
            raise BasketInputError(f"recipes.{index}.slug", "Tarif bulunamadı; /api/v1/recipes listesinden geçerli bir slug seçin.")
        selected.append(SelectedRecipe(**selection.model_dump(), selection_index=index,
            recipe_id=recipe.id, name=recipe.name, provenance=recipe.provenance))
        for ingredient in scale_recipe(recipe, selection.servings).scaled_ingredients:
            if ingredient.optional and request.optional_policy == "required_only":
                excluded += 1
                continue
            quantity, unit = normalize_quantity(ingredient.quantity, ingredient.unit)
            groups[ingredient.ingredient_id][unit].append(RecipeContribution(
                selection_index=index, recipe_id=recipe.id, slug=recipe.slug, name=recipe.name,
                servings=selection.servings, quantity=quantity, unit=unit, quantity_display=display_quantity(quantity, unit),
                source_quantity=ingredient.quantity, source_unit=ingredient.unit,
                optional=ingredient.optional, notes=ingredient.notes, provenance=recipe.provenance))
    items = []
    for ingredient_id in sorted(groups):
        definition = catalog.registry.get(ingredient_id)
        components = []
        units = set(groups[ingredient_id])
        stock = tuple(PantryStock(quantity=q, unit=u, display=display_quantity(q, u)) for (ident, u), q in sorted(pantry.quantities.items()) if ident == ingredient_id)
        known_units = {s.unit for s in stock if s.quantity > 0}
        incompatible = len(units | known_units) > 1
        unknown = ingredient_id in pantry.unknown
        warnings = []
        if incompatible:
            warnings.append("Uyumsuz birimler ayrı tutuldu; yoğunluk veya kaşık/bardak dönüşümü yapılmadı. Her bileşeni ayrı kontrol edin.")
        if unknown:
            warnings.append("Evde var · miktar bilinmiyor. Yalnızca doğrulanmış miktarlar ihtiyaçtan düşüldü.")
        if not definition.quantity_subtraction_supported:
            warnings.append("Bu malzemede miktar çıkarımı desteklenmiyor; eksik miktar ihtiyacın tamamı olarak korundu.")
        for unit in sorted(units):
            contributions = tuple(groups[ingredient_id][unit])
            required = sum((c.quantity for c in contributions), Decimal(0))
            mandatory = sum((c.quantity for c in contributions if not c.optional), Decimal(0))
            available = pantry.quantities.get((ingredient_id, unit), Decimal(0))
            allocated = min(required, available) if definition.quantity_subtraction_supported else Decimal(0)
            missing = required - allocated
            status = "exact"
            if not definition.quantity_subtraction_supported:
                status = "unresolved"
            elif unknown and missing > 0:
                status = "presence_only"
            available_value = None if unknown and (ingredient_id, unit) not in pantry.quantities else available
            required_text = display_quantity(required, unit)
            allocated_text = display_quantity(allocated, unit)
            missing_text = display_quantity(missing, unit)
            components.append(QuantityComponent(unit=unit, unit_label=UNIT_LABELS[unit],
                required_quantity=required, mandatory_quantity=mandatory, optional_quantity=required-mandatory,
                pantry_available_quantity=available_value, pantry_allocated_quantity=allocated, missing_quantity=missing,
                calculation_status=status, contributions=contributions, required_display=required_text,
                available_display="Miktar bilinmiyor" if available_value is None else display_quantity(available, unit),
                allocated_display=allocated_text, missing_display=missing_text,
                explanation=f"Tarif katkıları toplamı {required_text} − ayrılan stok {allocated_text} = kalan ihtiyaç {missing_text}."))
        statuses = {c.calculation_status for c in components}
        item_status = "unresolved" if "unresolved" in statuses else "incompatible_units" if incompatible else "presence_only" if "presence_only" in statuses else "exact"
        all_contributions = [c for component in components for c in component.contributions]
        flags = {c.optional for c in all_contributions}
        items.append(BasketItem(ingredient_id=ingredient_id, name=definition.name, category=definition.category,
            components=tuple(components), pantry_stock=stock + ((PantryStock(quantity=None, unit=None, display="Evde var · miktar bilinmiyor"),) if unknown else ()),
            unknown_pantry_quantity=unknown, optional_status="mixed" if len(flags)>1 else "optional" if True in flags else "required",
            calculation_status=item_status, warnings=tuple(warnings)))
    summary = BasketSummary(selected_recipe_count=len(selected), total_servings=sum(s.servings for s in selected),
        unique_ingredients=len(items),
        fully_covered=sum(all(c.missing_quantity == 0 for c in i.components) and i.calculation_status == "exact" for i in items),
        partially_covered=sum(any(c.pantry_allocated_quantity > 0 for c in i.components) and any(c.missing_quantity > 0 for c in i.components) for i in items),
        items_to_buy=sum(any(c.missing_quantity > 0 for c in i.components) for i in items),
        unresolved_items=sum(i.calculation_status != "exact" for i in items))
    return BasketPreview(items=tuple(items), selected_recipes=tuple(selected), optional_policy=request.optional_policy,
        excluded_optional_contributions=excluded, summary=summary)
