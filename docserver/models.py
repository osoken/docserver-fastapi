from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

from .utils import gen_datetime, gen_uuid, suuid_generator

id_type = String(suuid_generator.encoded_length())


def id_column_type():
    return Column(id_type, primary_key=True, default=gen_uuid)


def format_cursor_value(context):
    params = context.get_current_parameters()
    return f"{params['updated_at'].timestamp()}|{params.get('id', params.get('collections_id'))}"


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = id_column_type()
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = id_column_type()
    user_id = Column(id_type, ForeignKey(User.id))
    token = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)

    user = relationship("User", backref=backref("token", uselist=False))


class Collection(Base):
    __tablename__ = "collections"

    id = id_column_type()
    owner_id = Column(id_type, ForeignKey(User.id))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)
    cursor_value = Column(
        String, default=format_cursor_value, onupdate=format_cursor_value, index=True, unique=True, nullable=False
    )

    user = relationship("User", backref=backref("collections"))
