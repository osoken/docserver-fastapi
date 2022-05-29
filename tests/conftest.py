from typing import Any, Callable, Dict, Generator, Optional
from uuid import uuid4

import pytest
from docserver import config, models, schema, utils
from docserver.app import generate_app
from docserver.deps import SessionHandler
from factory.alchemy import SQLAlchemyModelFactory
from factory.fuzzy import FuzzyAttribute
from fastapi import testclient
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pydantic_factories import ModelFactory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, scoped_session, sessionmaker


class TestingSession(Session):
    def commit(self):
        self.flush()
        self.expire_all()


class TestSessionHandler(SessionHandler):
    def __init__(self, settings: Optional[config.Settings] = None):
        super(TestSessionHandler, self).__init__(settings)
        self._session_id = uuid4().hex

    @property
    def sessionmaker(self) -> sessionmaker:
        if self._sessionmaker is None:
            self._sessionmaker = scoped_session(
                sessionmaker(class_=TestingSession, autocommit=False, autoflush=False, bind=self.engine),
                scopefunc=lambda: self._session_id,
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
        if data is not None and isinstance(data, BaseModel):
            return super().post(
                url,
                data=schema.json_encoder.encode(data.dict()),
                json=None,
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
def settings() -> Generator:
    yield config.get_setting(DB_DBNAME="test")


@pytest.fixture(scope="function")
def db(test_db, settings) -> Generator:
    test_session_handler = TestSessionHandler(settings=settings)

    models.Base.metadata.create_all(test_session_handler.engine)

    yield test_session_handler

    test_session_handler.engine.dispose()


@pytest.fixture(scope="function")
def app(db, settings) -> Generator:
    app_ = generate_app(settings)
    app_.dependency_overrides[app_.session_handler.get_db] = db.get_db
    yield app_


@pytest.fixture(scope="function")
def client(app) -> Generator:
    yield DocServerTestClient(app)


@pytest.fixture(scope="function")
def factories(db) -> Generator:
    class UserCreateQueryFactory(DocServerModelFactory):
        __model__ = schema.UserCreateQuery

    class UserLoginQueryFactory(DocServerModelFactory):
        __model__ = schema.UserLoginQuery

    class UserFactory(SQLAlchemyModelFactory):
        class Meta:
            model = models.User
            sqlalchemy_session = db.sessionmaker
            sqlalchemy_session_persistence = "commit"

        hashed_password = FuzzyAttribute(lambda: schema._get_hashed_value(utils.gen_password(16)))

    class RefreshTokenFactory(SQLAlchemyModelFactory):
        class Meta:
            model = models.RefreshToken
            sqlalchemy_session = db.sessionmaker
            sqlalchemy_session_persistence = "commit"

    class Factories:
        def __init__(self):
            self.UserCreateQueryFactory = UserCreateQueryFactory
            self.UserFactory = UserFactory
            self.UserLoginQueryFactory = UserLoginQueryFactory
            self.RefreshTokenFactory = RefreshTokenFactory

    yield Factories()

    db.engine.dispose()


@pytest.fixture(scope="function")
def fixture_users(factories) -> Generator:
    factories.UserFactory(
        id="0123456789abcdefABCDEF",
        username="testuser",
        email="test@somewhere.com",
        hashed_password=schema._get_hashed_value("p@ssW0rd"),
    )
    yield None
    factories.UserFactory._meta.sqlalchemy_session.close()


@pytest.fixture(scope="function")
def fixture_refresh_token(factories, fixture_users) -> Generator:
    factories.RefreshTokenFactory(
        id="1234567890abcdefABCDEF", user_id="0123456789abcdefABCDEF", token="the_refresh_token"
    )
    yield None
    factories.UserFactory._meta.sqlalchemy_session.close()
