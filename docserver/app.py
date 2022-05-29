from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import operators, schema, utils
from .config import get_setting
from .deps import SessionHandler


def generate_app(settings=None):
    if settings is None:
        return generate_app(get_setting())
    app = FastAPI(title='document server', openapi_url=f"{settings.API_V1_STR}/openapi.json")
    app.settings = settings
    app.session_handler = SessionHandler(settings)

    @app.post("/api/v1/users", response_model=schema.UserRetrieveResponse)
    def create_user(data: schema.UserCreateQuery, db: Session = Depends(app.session_handler.get_db)):
        try:
            return operators.create_user(db, data)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @app.post("/api/v1/token", response_model=schema.TokenResponse)
    def get_token(data: schema.UserLoginQuery, db: Session = Depends(app.session_handler.get_db)):
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

    return app
