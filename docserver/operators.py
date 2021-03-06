import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Optional, Union

from jose import jwt
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import or_

from . import models, schema, types


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


def authenticate_user(db: Session, query: schema.UserLoginQuery) -> Union[models.User, None]:
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


def get_user_by_refresh_token(
    db: Session, refresh_token: str, secret_key: str, algorithm: str
) -> Union[models.User, None]:
    refresh_token_record = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_token).first()
    if refresh_token_record is None:
        return None
    try:
        payload = jwt.decode(refresh_token, key=secret_key, algorithms=[algorithm])
        uid_in_payload = re.sub("^userId:", "", payload.get("sub"))
        if refresh_token_record.user_id != uid_in_payload:
            return None
    except ExpiredSignatureError:
        return None
    return db.query(models.User).get(refresh_token_record.user_id)


def get_user_by_access_token(
    db: Session, access_token: str, secret_key: str, algorithm: str
) -> Union[models.User, None]:
    try:
        payload = jwt.decode(access_token, key=secret_key, algorithms=[algorithm])
        uid_in_payload = re.sub("^userId:", "", payload.get("sub"))
    except ExpiredSignatureError:
        return None
    return db.query(models.User).get(uid_in_payload)


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
            assert user_id == uid_in_payload
            return refresh_token_record.token
        except ExpiredSignatureError:
            pass
    encoded_jwt = create_access_token(
        {"sub": f"userId:{user_id}"}, expires_delta=expires_delta, secret_key=secret_key, algorithm=algorithm
    )
    if refresh_token_record is None:
        refresh_token_record = models.RefreshToken(user_id=user_id, token=encoded_jwt)
        db.add(refresh_token_record)
    else:
        refresh_token_record.token = encoded_jwt
    db.commit()
    db.refresh(refresh_token_record)
    return refresh_token_record.token


def create_collection(db: Session, data: schema.CollectionCreateQuery, user: models.User) -> models.Collection:
    collection = models.Collection(name=data.name, owner_id=user.id)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def list_collections(db: Session, user: models.User, cursor: Optional[types.EncodedCursor] = None, page_size: int = 10):
    q = db.query(models.Collection).filter(models.Collection.owner_id == user.id)
    if cursor is not None:
        decoded_cursor = cursor.decode_cursor()
        if decoded_cursor.direction == "n":
            res = list(
                q.filter(models.Collection.cursor_value <= decoded_cursor.cursor_value)
                .order_by(models.Collection.cursor_value.desc())
                .limit(page_size)
            )
        elif decoded_cursor.direction == "p":
            res = sorted(
                q.filter(models.Collection.cursor_value >= decoded_cursor.cursor_value)
                .order_by(models.Collection.cursor_value)
                .limit(page_size),
                key=lambda d: d.cursor_value,
                reverse=True,
            )
        else:
            raise ValueError("invalid direction")
    else:
        res = list(q.order_by(models.Collection.cursor_value.desc()).limit(page_size))

    if len(res) == 0:
        b0 = None
        b1 = None
    else:
        b0 = (
            q.filter(models.Collection.cursor_value < res[-1].cursor_value)
            .order_by(models.Collection.cursor_value.desc())
            .first()
        )
        b1 = (
            q.filter(models.Collection.cursor_value > res[0].cursor_value)
            .order_by(models.Collection.cursor_value)
            .first()
        )
    res = {
        "meta": {
            "count": q.count(),
            "next_cursor": types.DecodedCursor("n", b0.cursor_value) if b0 is not None else None,
            "prev_cursor": types.DecodedCursor("p", b1.cursor_value) if b1 is not None else None,
        },
        "results": list(res),
    }
    return res


def retrieve_collection(db: Session, user: models.User, collection_id: schema.ShortUUID):
    return (
        db.query(models.Collection)
        .filter(models.Collection.owner_id == user.id, models.Collection.id == collection_id)
        .first()
    )


def update_collection(
    db: Session, user: models.User, collection_id: schema.ShortUUID, data: schema.CollectionUpdateQuery
):
    collection = retrieve_collection(db, user, collection_id)
    if collection is None:
        return None
    collection.name = data.name
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(db: Session, user: models.User, collection_id: schema.ShortUUID):
    collection = retrieve_collection(db, user, collection_id)
    if collection is None:
        return None
    res = collection.id
    db.delete(collection)
    db.commit()
    return res


def create_item(db: Session, user: models.User, collection_id: schema.ShortUUID, data: schema.ItemCreateQuery):
    collection = retrieve_collection(db, user, collection_id)
    if collection is None:
        return None
    item = models.Item(collection_id=collection.id, owner_id=user.id, data_type=data.data_type)
    item.body = data.body.decode_to_binary()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def retrieve_item(db: Session, user: models.User, collection_id: schema.ShortUUID, item_id: schema.ShortUUID):
    return (
        db.query(models.Item)
        .filter(models.Item.collection_id == collection_id, models.Item.id == item_id, models.Item.owner_id == user.id)
        .first()
    )


def update_item(
    db: Session,
    user: models.User,
    collection_id: schema.ShortUUID,
    item_id: schema.ShortUUID,
    data: schema.ItemUpdateQuery,
):
    item = retrieve_item(db, user, collection_id, item_id)
    if item is None:
        return None
    mutated = False
    if data.data_type is not None:
        item.data_type = data.data_type
        mutated = True
    if data.body is not None:
        item.body = data.body.decode_to_binary()
        mutated = True
    if mutated:
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def delete_item(db: Session, user: models.User, collection_id: schema.ShortUUID, item_id: schema.ShortUUID):
    item = retrieve_item(db, user, collection_id, item_id)
    if item is None:
        return None
    res = item.id
    db.delete(item)
    db.commit()
    return res


def list_items(
    db: Session,
    user: models.User,
    collection_id: schema.ShortUUID,
    cursor: Optional[types.EncodedCursor] = None,
    page_size: int = 10,
):
    collection = retrieve_collection(db, user, collection_id)
    if collection is None:
        return None

    q = db.query(models.Item).filter(models.Item.owner_id == user.id, models.Item.collection_id == collection_id)
    if cursor is not None:
        decoded_cursor = cursor.decode_cursor()
        if decoded_cursor.direction == "n":
            res = list(
                q.filter(models.Item.cursor_value <= decoded_cursor.cursor_value)
                .order_by(models.Item.cursor_value.desc())
                .limit(page_size)
            )
        elif decoded_cursor.direction == "p":
            res = sorted(
                q.filter(models.Item.cursor_value >= decoded_cursor.cursor_value)
                .order_by(models.Item.cursor_value)
                .limit(page_size),
                key=lambda d: d.cursor_value,
                reverse=True,
            )
        else:
            raise ValueError("invalid direction")
    else:
        res = list(q.order_by(models.Item.cursor_value.desc()).limit(page_size))

    if len(res) == 0:
        b0 = None
        b1 = None
    else:
        b0 = q.filter(models.Item.cursor_value < res[-1].cursor_value).order_by(models.Item.cursor_value.desc()).first()
        b1 = q.filter(models.Item.cursor_value > res[0].cursor_value).order_by(models.Item.cursor_value).first()
    res = {
        "meta": {
            "count": q.count(),
            "next_cursor": types.DecodedCursor("n", b0.cursor_value) if b0 is not None else None,
            "prev_cursor": types.DecodedCursor("p", b1.cursor_value) if b1 is not None else None,
        },
        "results": list(res),
    }
    return res
