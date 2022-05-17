from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from . import operators, schema, utils
from .config import get_setting
from .deps import SessionHandler


def generate_app():
    settings = get_setting()
    app = FastAPI(title='document server', openapi_url=f"{settings.API_V1_STR}/openapi.json")
    app.settings = settings
    app.session_handler = SessionHandler(settings)

    @app.post("/api/v1/users", response_model=schema.UserRetrieveResponse)
    def create_user(data: schema.UserCreateQuery, db: Session = Depends(app.session_handler.get_db)):
        return operators.create_user(db, data)

    return app
