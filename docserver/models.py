from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

from .utils import gen_timestamp, gen_uuid, suuid_generator

id_column_type = Column(String(suuid_generator.encoded_length()), primary_key=True, default=gen_uuid)


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = id_column_type
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=gen_timestamp)
    updated_at = Column(DateTime, nullable=False, default=gen_timestamp, onupdate=gen_timestamp)
