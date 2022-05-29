from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

from .utils import gen_timestamp, gen_uuid, suuid_generator

id_type = String(suuid_generator.encoded_length())


def id_column_type():
    return Column(id_type, primary_key=True, default=gen_uuid)


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = id_column_type()
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=gen_timestamp)
    updated_at = Column(DateTime, nullable=False, default=gen_timestamp, onupdate=gen_timestamp)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = id_column_type()
    user_id = Column(id_type, ForeignKey(User.id))
    token = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=gen_timestamp)
    updated_at = Column(DateTime, nullable=False, default=gen_timestamp, onupdate=gen_timestamp)

    user = relationship("User", backref=backref("token", uselist=False))
