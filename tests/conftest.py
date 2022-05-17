from typing import Generator
from uuid import uuid4

import pytest
from docserver import config, db, models
from docserver.app import generate_app
from docserver.deps import SessionHandler
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.session import close_all_sessions


class TestingSession(Session):
    def commit(self):
        self.flush()
        self.expire_all()


class TestSessionHandler(SessionHandler):
    @property
    def sessionmaker(self) -> sessionmaker:
        if self._sessionmaker is None:
            self._sessionmaker = sessionmaker(
                class_=TestingSession, autocommit=False, autoflush=False, bind=self.engine
            )
        return self._sessionmaker

    def get_db(self) -> Generator:
        db = self.sessionmaker()
        try:
            yield db
            db.commit()
        except SQLAlchemyError as e:
            assert e is not None
            db.rollback()
        finally:
            db.close()


@pytest.fixture(scope="session")
def test_db() -> Generator:
    settings = config.get_setting()
    session_handler = SessionHandler(settings=settings)
    conn = session_handler.engine.connect()
    conn.execute("commit")
    try:
        conn.execute("drop database test")
    except SQLAlchemyError as e:
        pass
    finally:
        conn.close()

    conn = session_handler.engine.connect()
    conn.execute("commit")
    conn.execute("create database test")
    conn.close()

    yield 1

    conn = session_handler.engine.connect()
    conn.execute("commit")
    conn.execute("drop database test")
    conn.close()


@pytest.fixture(scope="session")
def db(test_db) -> Generator:
    test_settings = config.get_setting(DB_DBNAME="test")
    test_session_handler = TestSessionHandler(settings=test_settings)

    models.Base.metadata.create_all(test_session_handler.engine)

    yield test_session_handler

    test_session_handler.engine.dispose()


@pytest.fixture(scope="session")
def app(db) -> Generator:
    app_ = generate_app()
    app_.dependency_overrides[app_.session_handler.get_db] = db.get_db
    yield app_


@pytest.fixture(scope="function")
def client(app) -> Generator:
    yield TestClient(app)
