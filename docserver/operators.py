import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Union

from jose import jwt
from jose.exceptions import ExpiredSignatureError
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


def create_access_token(data: Mapping[str, str], expires_delta: timedelta, secret_key: str, algorithm: str) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, key=secret_key, algorithm=algorithm)
    return encoded_jwt


def get_or_create_refresh_token(
    db: Session, user_id: schema.ShortUUID, expires_delta: timedelta, secret_key: str, algorithm: str
) -> str:
    refresh_token_record = db.query(models.RefreshToken).filter_by(user_id=user_id).one_or_none()
    if refresh_token_record is not None:
        try:
            payload = jwt.decode(refresh_token_record.token, key=secret_key, algorithms=[algorithm])
            uid_in_payload = re.sub("^userId:", "", payload.get("sub"))
            if user_id != uid_in_payload:
                refresh_token_record = None
        except ExpiredSignatureError:
            refresh_token_record = None
    if refresh_token_record is None:
        encoded_jwt = create_access_token(
            {"sub": f"userId:{user_id}"}, expires_delta=expires_delta, secret_key=secret_key, algorithm=algorithm
        )
        refresh_token_record = models.RefreshToken(user_id=user_id, token=encoded_jwt)
        db.add(refresh_token_record)
        db.commit()
        db.refresh(refresh_token_record)
    return refresh_token_record.token
