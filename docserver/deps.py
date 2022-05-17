from typing import Generator, Optional

from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker

from . import config
from .db import setup_engine, setup_sessionmaker


class SessionHandler:
    def __init__(self, settings: Optional[config.Settings] = None):
        self._settings = settings
        self._engine = None
        self._sessionmaker = None

    @property
    def settings(self) -> config.Settings:
        if self._settings is None:
            self._settings = config.get_setting()
        return self._settings

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = setup_engine(self.settings.SQLALCHEMY_DATABASE_URI)
        return self._engine

    @property
    def sessionmaker(self) -> sessionmaker:
        if self._sessionmaker is None:
            self._sessionmaker = setup_sessionmaker(self.engine)
        return self._sessionmaker

    def get_db(self) -> Generator:
        db = self.sessionmaker()
        try:
            yield db
        finally:
            db.close()
