from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Union

from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import or_

from . import models, schema


def create_user(db: Session, query: schema.UserCreateQuery) -> schema.UserRetrieveResponse:
    if db.query(
        db.query(models.User)
        .filter(or_(models.User.username == query.username, models.User.email == query.email))
        .exists()
    ).scalar():
        raise ValueError("username and/or email already exists.")
    user = models.User(username=query.username, hashed_password=query.password.get_hashed_value(), email=query.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return schema.UserRetrieveResponse.from_orm(user)


def authenticate_user(db: Session, query: schema.UserLoginQuery) -> Union[schema.UserRetrieveResponse, None]:
    if query.is_username():
        user = db.query(models.User).filter(models.User.username == query.login_id).first()
    else:
        user = db.query(models.User).filter(models.User.email == query.login_id).first()
    if user is None:
        return None
    if query.password.verify_with_hashed_value(user.hashed_password):
        return schema.UserRetrieveResponse(
            id=user.id, username=user.username, email=user.email, created_at=user.created_at, updated_at=user.updated_at
        )
    return None


def create_access_token(data: Mapping[str, str], expires_delta: timedelta, secret_key: str, algorithm: str):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt
