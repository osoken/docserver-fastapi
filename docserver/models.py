import math

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship

from .utils import format_cursor_value, gen_datetime, gen_uuid, suuid_generator

id_type = String(suuid_generator.encoded_length())

chunk_size = 1024 * 1024 * 16


def id_column_type():
    return Column(id_type, primary_key=True, default=gen_uuid)


class CursorValueFormatter:
    def __init__(self, target: str):
        self._target = target

    def __call__(self, context):
        params = context.get_current_parameters()
        return format_cursor_value(params["updated_at"], params.get("id", params.get(self._target)))


collection_cursor_value_formatter = CursorValueFormatter("collection_id")
item_cursor_value_formatter = CursorValueFormatter("item_id")

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
    user_id = Column(id_type, ForeignKey(User.id, ondelete="CASCADE"))
    token = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)

    user = relationship("User", backref=backref("token", uselist=False))


class Collection(Base):
    __tablename__ = "collections"

    id = id_column_type()
    owner_id = Column(id_type, ForeignKey(User.id, ondelete="CASCADE"))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)
    cursor_value = Column(
        String,
        default=collection_cursor_value_formatter,
        onupdate=collection_cursor_value_formatter,
        index=True,
        unique=True,
        nullable=False,
    )

    user = relationship("User", backref=backref("collections"))


class Item(Base):
    __tablename__ = "items"

    id = id_column_type()
    owner_id = Column(id_type, ForeignKey(User.id, ondelete="CASCADE"))
    collection_id = Column(id_type, ForeignKey(Collection.id, ondelete="CASCADE"))
    data_type = Column(String)
    created_at = Column(DateTime, nullable=False, default=gen_datetime)
    updated_at = Column(DateTime, nullable=False, default=gen_datetime, onupdate=gen_datetime)
    cursor_value = Column(
        String,
        default=item_cursor_value_formatter,
        onupdate=item_cursor_value_formatter,
        index=True,
        unique=True,
        nullable=False,
    )

    chunks = relationship(
        "Chunk", cascade="all, delete", order_by="Chunk.index", backref='item', lazy=True, uselist=True
    )

    @hybrid_property
    def body(self):
        return b''.join((d.body for d in self.chunks))

    @body.setter
    def body(self, value: bytes):
        self.chunks = [
            Chunk(item=self, index=i, body=value[(i * chunk_size) : min(len(value), (i + 1) * chunk_size)])
            for i in range(math.ceil(len(value) / chunk_size))
        ]
        if self.updated_at is not None:
            self.updated_at = gen_datetime()


class Chunk(Base):
    __tablename__ = "chunks"

    id = id_column_type()
    item_id = Column(id_type, ForeignKey(Item.id, ondelete="CASCADE"))
    index = Column(Integer)
    body = Column(LargeBinary)

    __table_args__ = (Index("uk_chunk_item_id_index", "item_id", "index", unique=True),)
