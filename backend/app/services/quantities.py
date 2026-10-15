from decimal import Decimal, localcontext
from app.schemas.recipes import Dimension, Unit, UNIT_LABELS

# Culinary measures are deliberately independent, even within the same dimension.
NORMAL_UNITS = {Unit.G: (Dimension.MASS, Unit.G, Decimal(1)),
    Unit.KG: (Dimension.MASS, Unit.G, Decimal(1000)),
    Unit.ML: (Dimension.VOLUME, Unit.ML, Decimal(1)),
    Unit.L: (Dimension.VOLUME, Unit.ML, Decimal(1000)),
    Unit.PIECE: (Dimension.COUNT, Unit.PIECE, Decimal(1))}


def normalize_quantity(quantity: Decimal, unit: Unit) -> tuple[Decimal, Unit]:
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity < 0:
        raise ValueError("Quantity must be a finite, nonnegative Decimal")
    unit = Unit(unit)
    _, canonical, factor = NORMAL_UNITS.get(unit, (Dimension.CULINARY, unit, Decimal(1)))
    with localcontext() as context:
        context.prec = 28
        return quantity * factor, canonical


def dimension(unit: Unit) -> Dimension:
    return NORMAL_UNITS.get(Unit(unit), (Dimension.CULINARY, unit, Decimal(1)))[0]


def display_quantity(quantity: Decimal, unit: Unit) -> str:
    # Preserve calculation precision; never parse this string for arithmetic.
    value = format(quantity, "f")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value.replace(".", ",") + " " + UNIT_LABELS[unit]
