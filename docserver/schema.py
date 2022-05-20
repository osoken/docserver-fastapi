import re
from datetime import datetime
from json import JSONEncoder
from typing import Any, Union

from humps import camelize
from passlib.context import CryptContext
from pydantic import EmailStr, SecretStr, constr
from pydantic.generics import GenericModel

from .utils import suuid_generator

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
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[`~!@#$%^&*()-_+={[\]|:;\"'<,>.?/}])[A-Za-z\d`~!@#$%^&*()-_+={[\]|:;\"'<,>.?/}]{8,32}$",
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


class UserCreateQuery(GenericCamelModel):
    username: UsernameString
    email: EmailStr
    password: PasswordString


class UserLoginQuery(GenericCamelModel):
    login_id: Union[UsernameString, EmailStr]
    password: SecretStr

    def is_username(self) -> bool:
        try:
            UsernameString.validate(value=self.login_id)
            return True
        except ValueError as _:
            return False

    def is_email(self) -> bool:
        try:
            EmailStr.validate(value=self.login_id)
            return True
        except ValueError as _:
            return False


class UserRetrieveResponse(GenericCamelModel):
    id: ShortUUID
    username: UsernameString
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DocServerJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, PasswordString):
            return o.get_secret_value()
        return super(DocServerJSONEncoder, self).default(o)


json_encoder = DocServerJSONEncoder()
