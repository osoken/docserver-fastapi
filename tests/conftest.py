from typing import Any, Callable, Dict, Generator

import pytest
from docserver import config, models, schema, utils
from docserver.app import generate_app
from docserver.deps import SessionHandler
from factory.alchemy import SQLAlchemyModelFactory
from fastapi import testclient
from fastapi.testclient import TestClient
from pydantic_factories import ModelFactory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


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


class DocServerModelFactory(ModelFactory):
    @classmethod
    def get_provider_map(cls) -> Dict[Any, Callable]:
        m = super().get_provider_map()
        m[schema.PasswordString] = lambda: utils.gen_password(10)
        return m


class DocServerTestClient(TestClient):
    def post(
        self,
        url,
        data=None,
        json=None,
        *,
        params=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=None,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
    ):
        if json is not None:
            return super().post(
                url,
                schema.json_encoder.encode(json),
                None,
                params=params,
                headers=headers,
                cookies=cookies,
                files=files,
                auth=auth,
                timeout=timeout,
                allow_redirects=allow_redirects,
                proxies=proxies,
                hooks=hooks,
                stream=stream,
                verify=verify,
                cert=cert,
            )
        return super().post(
            url,
            data,
            json,
            params=params,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
        )


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
    yield DocServerTestClient(app)


@pytest.fixture(scope="session")
def factories(db) -> Generator:
    sess = db.sessionmaker()

    class UserCreateQueryFactory(DocServerModelFactory):
        __model__ = schema.UserCreateQuery

    class UserFactory(SQLAlchemyModelFactory):
        class Meta:
            model = models.User
            sqlalchemy_session = sess

    class Factories:
        def __init__(self):
            self.UserCreateQueryFactory = UserCreateQueryFactory
            self.UserFactory = UserFactory

    yield Factories()
