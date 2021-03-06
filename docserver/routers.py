from datetime import timedelta
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import config, deps, models, operators, schema, types


def generate_router(
    settings: config.Settings, session_handler: deps.SessionHandler, oauth2_scheme: OAuth2PasswordBearer
):
    router = APIRouter()

    async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(session_handler.get_db)):
        user = operators.get_user_by_access_token(db, token, settings.SECRET_KEY, settings.ALGORITHM)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    @router.post("/users", response_model=schema.UserRetrieveResponse)
    def create_user(data: schema.UserCreateQuery, db: Session = Depends(session_handler.get_db)):
        try:
            return operators.create_user(db, data)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/token", response_model=schema.TokenResponse)
    def get_token(
        data: Union[schema.UserLoginQuery, schema.RefreshTokenQuery],
        db: Session = Depends(session_handler.get_db),
    ):
        if isinstance(data, schema.UserLoginQuery):
            user = operators.authenticate_user(db, data)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect login_id or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            refresh_token = operators.get_or_create_refresh_token(
                db,
                user_id=user.id,
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                secret_key=settings.SECRET_KEY,
                algorithm=settings.ALGORITHM,
            )
        else:
            user = operators.get_user_by_refresh_token(
                db, data.refresh_token, secret_key=settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            refresh_token = data.refresh_token

        access_token = operators.create_access_token(
            data={"sub": f"userId:{user.id}"},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    @router.post("/login", response_model=schema.LoginResponse)
    def login_by_password(
        db: Session = Depends(session_handler.get_db), form_data: OAuth2PasswordRequestForm = Depends()
    ):
        user = operators.authenticate_user(
            db, schema.UserLoginQuery(login_id=form_data.username, password=form_data.password)
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect login_id or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        refresh_token = operators.get_or_create_refresh_token(
            db,
            user_id=user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        access_token = operators.create_access_token(
            data={"sub": f"userId:{user.id}"},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    @router.get("/users/me", response_model=schema.UserRetrieveResponse)
    def get_users_me(
        db: Session = Depends(session_handler.get_db), current_user: models.User = Depends(get_current_user)
    ):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return schema.UserRetrieveResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
        )

    @router.post("/collections", response_model=schema.CollectionRetrieveResponse)
    def create_collection(
        data: schema.CollectionCreateQuery,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        return operators.create_collection(db, data, current_user)

    @router.put("/collections/{collection_id}", response_model=schema.CollectionRetrieveResponse)
    def update_collection(
        collection_id: schema.ShortUUID,
        data: schema.CollectionUpdateQuery,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.update_collection(db, current_user, collection_id, data)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such collection")
        return schema.CollectionRetrieveResponse.from_orm(res)

    @router.delete("/collections/{collection_id}")
    def delete_collection(
        collection_id: schema.ShortUUID,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.delete_collection(db, current_user, collection_id)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such collection")

    @router.get("/collections", response_model=schema.CollectionListResponse)
    def list_collections(
        cursor: Optional[types.EncodedCursor] = None,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        return operators.list_collections(db, current_user, cursor=cursor)

    @router.get("/collections/{collection_id}", response_model=schema.CollectionRetrieveResponse)
    def retrieve_collection(
        collection_id: schema.ShortUUID,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.retrieve_collection(db, current_user, collection_id=collection_id)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such collection")
        return schema.CollectionRetrieveResponse.from_orm(res)

    @router.get("/collections/{collection_id}/items", response_model=schema.ItemListResponse)
    def list_items(
        collection_id: schema.ShortUUID,
        cursor: Optional[types.EncodedCursor] = None,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.list_items(db, current_user, collection_id, cursor=cursor)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such collection")
        return res

    @router.post("/collections/{collection_id}/items", response_model=schema.ItemHeaderResponse)
    def create_item(
        collection_id: schema.ShortUUID,
        data: schema.ItemCreateQuery,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        try:
            res = operators.create_item(db, current_user, collection_id, data)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid data")
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such collection")
        return res

    @router.get("/collections/{collection_id}/items/{item_id}", response_model=schema.ItemDetailResponse)
    def retrieve_item(
        collection_id: schema.ShortUUID,
        item_id: schema.ShortUUID,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.retrieve_item(db, current_user, collection_id, item_id)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such item")
        return schema.ItemDetailResponse.from_orm(res)

    @router.put("/collections/{collection_id}/items/{item_id}", response_model=schema.ItemHeaderResponse)
    def retrieve_item(
        collection_id: schema.ShortUUID,
        item_id: schema.ShortUUID,
        data: schema.ItemUpdateQuery,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        try:
            res = operators.update_item(db, current_user, collection_id, item_id, data)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid data")
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such item")
        return schema.ItemHeaderResponse.from_orm(res)

    @router.delete("/collections/{collection_id}/items/{item_id}")
    def delete_item(
        collection_id: schema.ShortUUID,
        item_id: schema.ShortUUID,
        db: Session = Depends(session_handler.get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        res = operators.delete_item(db, current_user, collection_id, item_id)
        if res is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such item")

    return router
