from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User
from app.schemas.baskets import BasketRequest
from app.schemas.users import SavedBasketRequest
from app.schemas.markets import Retailer, Product, PriceRequest, SavedPriceRequest, PriceResponse, ComparisonResponse
from app.services.auth import current_user
from app.services.baskets import preview_basket
from app.services.pricing import price_basket, compare_basket
from app.services.user_baskets import saved_basket

router = APIRouter(tags=["demo markets"])


def active_market(request, retailer_id):
    market = request.app.state.markets.find(retailer_id)
    if market is None or not market.active:
        raise HTTPException(404, "Demo market bulunamadı; /api/v1/markets listesinden seçin.")
    return market


@router.get("/markets",response_model=list[Retailer])
def markets(request: Request):
    return sorted((r for r in request.app.state.markets.retailers if r.active),key=lambda r:r.id)


@router.get("/markets/{retailer_id}/products",response_model=list[Product])
def products(retailer_id: str, request: Request):
    active_market(request,retailer_id)
    return sorted((p for p in request.app.state.markets.products if p.retailer_id==retailer_id),key=lambda p:p.id)


@router.post("/baskets/price",response_model=PriceResponse)
def price(body: PriceRequest,request: Request):
    market = active_market(request,body.retailer_id)
    basket = preview_basket(request.app.state.catalog,BasketRequest.model_validate(body.model_dump(exclude={"retailer_id"})))
    return PriceResponse(basket=basket,estimate=price_basket(basket,request.app.state.markets,market))


@router.post("/baskets/compare",response_model=ComparisonResponse)
def compare(body: BasketRequest,request: Request):
    basket = preview_basket(request.app.state.catalog,body)
    return compare_basket(basket,request.app.state.markets)


@router.post("/me/baskets/price",response_model=PriceResponse)
def price_saved(body: SavedPriceRequest,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    market = active_market(request,body.retailer_id)
    basket = saved_basket(request.app.state.catalog,db,user.id,body)
    return PriceResponse(basket=basket,estimate=price_basket(basket,request.app.state.markets,market))


@router.post("/me/baskets/compare",response_model=ComparisonResponse)
def compare_saved(body: SavedBasketRequest,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    return compare_basket(saved_basket(request.app.state.catalog,db,user.id,body),request.app.state.markets)
