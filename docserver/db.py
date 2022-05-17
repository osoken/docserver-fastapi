from pydantic import PostgresDsn
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker


def setup_engine(database_uri: PostgresDsn) -> Engine:
    return create_engine(database_uri)


def setup_sessionmaker(engine: Engine) -> sessionmaker:
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
