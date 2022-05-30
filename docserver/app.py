from fastapi import FastAPI

from . import routers
from .config import get_setting
from .deps import SessionHandler


def generate_app(settings=None):
    if settings is None:
        return generate_app(get_setting())
    app = FastAPI(title='document server', openapi_url=f"{settings.API_V1_STR}/openapi.json")
    app.settings = settings
    app.session_handler = SessionHandler(settings)
    app.include_router(
        routers.generate_router(settings=app.settings, session_handler=app.session_handler), prefix=settings.API_V1_STR
    )

    return app
