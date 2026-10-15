from decimal import Decimal
from typing import Annotated, Literal
from pydantic import AwareDatetime, BeforeValidator, Field, field_serializer, model_validator
from app.schemas.recipes import DomainModel, Unit
from app.schemas.baskets import BasketRequest, BasketPreview
from app.schemas.users import SavedBasketRequest


def reject_float(value):
    if isinstance(value, float):
        raise ValueError("Use a decimal string, never a floating-point value")
    return value


Identifier = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)]
Price = Annotated[Decimal, BeforeValidator(reject_float), Field(gt=0, le=1000000, max_digits=9, decimal_places=2, allow_inf_nan=False)]
PackageQuantity = Annotated[Decimal, BeforeValidator(reject_float), Field(gt=0, le=1000000, max_digits=13, decimal_places=6, allow_inf_nan=False)]
DEMO_NOTICE = "Demo fiyatlar · Geliştirme verisi — canlı fiyat değildir. Vergi dahil varsayılan paket bedelleri; teslimat/diğer ücretler ve kampanyalar hesaplanmaz."


class Retailer(DomainModel):
    id: Identifier
    slug: Identifier
    name: str = Field(min_length=3, max_length=100)
    active: bool = Field(default=True, strict=True)
    data_source: Literal["curated_demo"] = "curated_demo"
    currency: Literal["TRY"] = "TRY"


class Product(DomainModel):
    id: Identifier
    retailer_id: Identifier
    name: str = Field(min_length=3, max_length=160)
    brand: str = Field(min_length=1, max_length=80)
    canonical_ingredient_id: str = Field(min_length=2, max_length=80)
    package_quantity: PackageQuantity
    package_unit: Unit
    price: Price
    currency: Literal["TRY"] = "TRY"
    availability: Literal["available", "unavailable"] = "available"
    observed_at: AwareDatetime
    source: Literal["curated_demo"] = "curated_demo"

    @model_validator(mode="after")
    def physical_package(self):
        if self.package_unit not in {Unit.G, Unit.KG, Unit.ML, Unit.L, Unit.PIECE}:
            raise ValueError("Market packages require mass, volume or count; no spoon/cup conversions")
        if self.package_unit == Unit.PIECE and self.package_quantity != self.package_quantity.to_integral_value():
            raise ValueError("Count packages must contain whole units")
        return self

    @field_serializer("price")
    def price_string(self, value): return format(value, ".2f")


class Purchase(DomainModel):
    product: Product
    package_count: int
    purchased_quantity: Decimal
    line_total: Decimal

    @field_serializer("line_total")
    def money(self, value): return format(value, ".2f")


class PricedItem(DomainModel):
    ingredient_id: str
    name: str
    optional_status: Literal["required", "optional", "mixed"]
    required_missing_quantity: Decimal
    unit: Unit
    calculation_status: str
    status: Literal["fulfilled", "unavailable", "incompatible_unit", "unresolved", "optimization_limit"]
    purchases: tuple[Purchase, ...] = ()
    package_count: int = 0
    purchased_quantity: Decimal | None = None
    surplus_quantity: Decimal | None = None
    line_total: Decimal | None = None
    message: str

    @field_serializer("line_total")
    def money(self, value): return None if value is None else format(value, ".2f")


class MarketEstimate(DomainModel):
    retailer: Retailer
    items: tuple[PricedItem, ...]
    total_required_ingredients: int
    fulfilled_count: int
    unavailable_count: int
    complete: bool
    # A partial subtotal is never presented as a full basket price.
    priced_subtotal: Decimal
    basket_total: Decimal | None
    currency: Literal["TRY"] = "TRY"
    warnings: tuple[str, ...] = (DEMO_NOTICE,)

    @field_serializer("priced_subtotal", "basket_total")
    def money(self, value): return None if value is None else format(value, ".2f")


class PriceRequest(BasketRequest):
    retailer_id: Identifier


class SavedPriceRequest(SavedBasketRequest):
    retailer_id: Identifier


class PriceResponse(DomainModel):
    mode: Literal["demo_market_estimate"] = "demo_market_estimate"
    basket: BasketPreview
    estimate: MarketEstimate
    notice: str = DEMO_NOTICE


class ComparisonResponse(DomainModel):
    mode: Literal["demo_market_comparison"] = "demo_market_comparison"
    basket: BasketPreview
    estimates: tuple[MarketEstimate, ...]
    recommended_retailer_id: str | None
    message: str
    notice: str = DEMO_NOTICE
