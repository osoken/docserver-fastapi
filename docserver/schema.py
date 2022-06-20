import re
from datetime import datetime
from json import JSONEncoder
from typing import Any, List, Optional, Union

from humps import camelize
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, SecretStr, constr
from pydantic.generics import GenericModel

from docserver import utils

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_hashed_value(password: str) -> str:
    return password_context.hash(password)


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


class GenericCamelModel(GenericModel):
    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True


UsernameString = constr(regex=r"^[a-zA-Z][0-9a-zA-Z_-]{2,31}$")

ShortUUID = constr(regex=r"^[0-9a-zA-Z]{22}$")


class PasswordString(SecretStr):
    @classmethod
    def validate(cls, value: Any) -> 'PasswordString':
        v = super().validate(value)
        if (
            re.match(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[`~!@#$%^&*()-_+={[\]|:;\"'<,>.?/}])"
                r"[A-Za-z\d`~!@#$%^&*()-_+={[\]|:;\"'<,>.?/}]{8,32}$",
                v.get_secret_value(),
            )
            is None
        ):
            raise ValueError("invalid password string")
        return v

    def get_hashed_value(self) -> str:
        return _get_hashed_value(self.get_secret_value())

    def verify_with_hashed_value(self, hashed_password: str) -> bool:
        return _verify_password(self.get_secret_value(), hashed_password)


class DecodedCursor(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    def __init__(self, v: str):
        self._direction, self._cursor_value = utils.parse_cursor(v)

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def cursor_value(self) -> str:
        return self._cursor_value

    @classmethod
    def validate(cls, value: Any) -> 'DecodedCursor':
        v = cls(value)
        if v.direction != "p" and v.direction != "n":
            raise ValueError("invalid direction character")
        return v

    def is_prev(self) -> bool:
        return self.direction == "p"

    def is_next(self) -> bool:
        return self.direction == "n"


class EncodedCursor(DecodedCursor):
    def __init__(self, v: str):
        super(EncodedCursor, self).__init__(utils.decode_cursor(v))


class UserCreateQuery(GenericCamelModel):
    username: UsernameString
    email: EmailStr
    password: PasswordString


class CollectionCreateQuery(GenericCamelModel):
    name: str


class UserLoginQuery(GenericCamelModel):
    login_id: Union[UsernameString, EmailStr]
    password: PasswordString

    def is_username(self) -> bool:
        try:
            UsernameString.validate(value=self.login_id)
            return True
        except ValueError:
            return False

    def is_email(self) -> bool:
        try:
            EmailStr.validate(value=self.login_id)
            return True
        except ValueError:
            return False


class RefreshTokenQuery(GenericCamelModel):
    refresh_token: str


class UserRetrieveResponse(GenericCamelModel):
    id: ShortUUID
    username: UsernameString
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TokenResponse(GenericCamelModel):
    access_token: str
    refresh_token: str
    token_type: str


class AccessTokenResponse(GenericCamelModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class CollectionDetailResponse(GenericCamelModel):
    id: ShortUUID
    name: str
    owner_id: ShortUUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CollectionListMeta(GenericCamelModel):
    count: int
    next_cursor: Optional[str]
    prev_cursor: Optional[str]


class CollectionListResponse(GenericCamelModel):
    meta: CollectionListMeta
    results: List[CollectionDetailResponse]


class DocServerJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, SecretStr):
            return o.get_secret_value()

        return super(DocServerJSONEncoder, self).default(o)


json_encoder = DocServerJSONEncoder()
