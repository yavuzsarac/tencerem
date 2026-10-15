from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User, UserPreferences, PantryEntry, AuthSession
from app.schemas.users import Credentials, PublicUser, Preferences, PantryCreate, PantryPatch, PantryView, MealIntent, SavedBasketRequest, PersonalizedResponse
from app.schemas.baskets import BasketRequest, BasketPreview
from app.services.auth import current_user, csrf, auth_settings, issue_session, verify_password, HASHER, DUMMY_HASH, COOKIE, token_digest, throttle_auth
from app.services.profiles import read_preferences, save_preferences, saved_pantry, overlay_pantry
from app.services.quantities import normalize_quantity
from app.services.baskets import preview_basket
from app.services.personalization import personalized_recommend, compatible

router = APIRouter(tags=["accounts"])

@router.post("/auth/register", response_model=PublicUser, status_code=201, dependencies=[Depends(csrf), Depends(throttle_auth)])
def register(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_settings(request)
    user = User(email=str(body.email),password_hash=HASHER.hash(body.password.get_secret_value()))
    try:
        db.add(user); db.flush()
        db.add(UserPreferences(user_id=user.id)); db.flush()
        issue_session(request,response,db,user); db.commit(); db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Bu e-posta ile hesap oluşturulamıyor. Giriş yapmayı deneyin.") from None
    return user

@router.post("/auth/login", response_model=PublicUser, dependencies=[Depends(csrf), Depends(throttle_auth)])
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_settings(request)
    user = db.scalar(select(User).where(User.email == str(body.email)))
    valid = verify_password(user.password_hash if user else DUMMY_HASH,body.password.get_secret_value())
    if user is None or not valid:
        raise HTTPException(401,"E-posta veya parola hatalı.")
    if HASHER.check_needs_rehash(user.password_hash): user.password_hash=HASHER.hash(body.password.get_secret_value())
    issue_session(request,response,db,user); db.commit()
    return user

@router.post("/auth/logout", status_code=204, dependencies=[Depends(csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings=auth_settings(request)
    token=request.cookies.get(COOKIE)
    if token: db.execute(delete(AuthSession).where(AuthSession.token_hash==token_digest(token,settings)))
    db.commit()
    response.delete_cookie(COOKIE,path="/",secure=settings.cookie_secure,httponly=True,samesite="lax")

@router.get("/me", response_model=PublicUser)
def me(user: User = Depends(current_user)):
    return user

@router.get("/me/preferences", response_model=Preferences)
def preferences(user: User = Depends(current_user), db: Session=Depends(get_db)):
    return read_preferences(db,user.id)

@router.put("/me/preferences", response_model=Preferences, dependencies=[Depends(csrf)])
def update_preferences(body: Preferences,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    return save_preferences(db,user.id,body,request.app.state.catalog.registry)


def pantry_view(row, catalog):
    definition=catalog.registry.get(row.ingredient_id)
    return PantryView(id=row.id,ingredient_id=row.ingredient_id,name=definition.name,preparation_state=definition.preparation_state,
        quantity=row.quantity,unit=row.unit,expiration_date=row.expiration_date,created_at=row.created_at,updated_at=row.updated_at)

@router.get("/me/pantry", response_model=list[PantryView])
def pantry_list(request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    return [pantry_view(row,request.app.state.catalog) for row in db.scalars(select(PantryEntry).where(PantryEntry.user_id==user.id).order_by(PantryEntry.ingredient_id))]

@router.post("/me/pantry", response_model=PantryView,status_code=201,dependencies=[Depends(csrf)])
def pantry_add(body: PantryCreate,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    if request.app.state.catalog.registry.get(body.ingredient_id) is None: raise HTTPException(422,"Kayıtlı bir malzeme seçin.")
    row=PantryEntry(user_id=user.id,**body.model_dump(exclude={"presence"}))
    db.add(row)
    try: db.commit(); db.refresh(row)
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Bu malzeme Mutfağım'da var. Mevcut kaydı düzenleyin.") from None
    return pantry_view(row,request.app.state.catalog)

@router.patch("/me/pantry/{item_id}",response_model=PantryView,dependencies=[Depends(csrf)])
def pantry_edit(item_id: UUID,body: PantryPatch,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    row=db.scalar(select(PantryEntry).where(PantryEntry.id==str(item_id),PantryEntry.user_id==user.id))
    if row is None: raise HTTPException(404,"Malzeme bulunamadı.")
    patch=body.model_dump(exclude_unset=True)
    new_unit=patch.get("unit",row.unit)
    if row.unit is not None and new_unit is not None and normalize_quantity(row.quantity,row.unit)[1] != normalize_quantity(row.quantity,new_unit)[1]:
        raise HTTPException(422,"Bu birimler dönüştürülemez. Hazırlık durumunu kontrol edin; miktar bilinmiyorsa miktar ve birimi birlikte null yapın.")
    if new_unit is not None and row.unit is not None and new_unit != row.unit and "quantity" not in patch:
        canonical,_=normalize_quantity(row.quantity,row.unit)
        factor,_=normalize_quantity(Decimal(1),new_unit)
        patch["quantity"]=canonical/factor
    merged={"ingredient_id":row.ingredient_id,"quantity":patch.get("quantity",row.quantity),"unit":new_unit,"expiration_date":patch.get("expiration_date",row.expiration_date)}
    validated=PantryCreate.model_validate(merged)
    for key,value in validated.model_dump(exclude={"ingredient_id","presence"}).items():setattr(row,key,value)
    db.commit(); db.refresh(row)
    return pantry_view(row,request.app.state.catalog)

@router.delete("/me/pantry/{item_id}",status_code=204,dependencies=[Depends(csrf)])
def pantry_delete(item_id: UUID,user: User=Depends(current_user),db: Session=Depends(get_db)):
    row=db.scalar(select(PantryEntry).where(PantryEntry.id==str(item_id),PantryEntry.user_id==user.id))
    if row is None: raise HTTPException(404,"Malzeme bulunamadı.")
    db.delete(row); db.commit()

@router.post("/me/recipes/recommend", response_model=PersonalizedResponse)
def recommend_saved(body: MealIntent,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    catalog=request.app.state.catalog
    pantry=overlay_pantry(saved_pantry(db,user.id),body.pantry_adjustments,catalog.registry)
    return personalized_recommend(catalog,read_preferences(db,user.id),body,pantry)

@router.post("/me/baskets/preview",response_model=BasketPreview)
def basket_saved(body: SavedBasketRequest,request: Request,user: User=Depends(current_user),db: Session=Depends(get_db)):
    catalog=request.app.state.catalog
    profile=read_preferences(db,user.id)
    for selected in body.recipes:
        recipe=catalog.find(selected.slug)
        if recipe is not None and not compatible(recipe,catalog,profile):
            raise HTTPException(422, "Seçilen tarif kayıtlı beslenme/alerji kısıtlarınıza uymuyor veya içerik bilgisi eksik.")
    pantry=overlay_pantry(saved_pantry(db,user.id),body.pantry_adjustments,catalog.registry)
    return preview_basket(catalog,BasketRequest(recipes=body.recipes,pantry=pantry,optional_policy=body.optional_policy))
