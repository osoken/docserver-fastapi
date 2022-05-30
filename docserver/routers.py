from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import config, deps, operators, schema


def generate_router(settings: config.Settings, session_handler: deps.SessionHandler):
    router = APIRouter()

    @router.post("/users", response_model=schema.UserRetrieveResponse)
    def create_user(data: schema.UserCreateQuery, db: Session = Depends(session_handler.get_db)):
        try:
            return operators.create_user(db, data)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/token", response_model=schema.TokenResponse)
    def get_token(data: schema.UserLoginQuery, db: Session = Depends(session_handler.get_db)):
        user = operators.authenticate_user(db, data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect login_id or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = operators.create_access_token(
            data={"sub": f"userId:{user.id}"},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        refresh_token = operators.get_or_create_refresh_token(
            db,
            user_id=user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    return router
