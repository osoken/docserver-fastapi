import binascii
from base64 import urlsafe_b64decode, urlsafe_b64encode
from logging.config import valid_ident
from typing import Any

from . import utils


class DecodedCursor:
    def __init__(self, direction: str, cursor_value: str):
        self._direction = direction
        self._cursor_value = cursor_value

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def cursor_value(self) -> str:
        return self._cursor_value

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any):
        if isinstance(v, DecodedCursor):
            val = v
        if isinstance(v, EncodedCursor):
            val = v.decode_cursor()
        utils.parse_cursor(utils.decode_cursor(v))
        return v

    def encode_cursor(self) -> "EncodedCursor":
        return EncodedCursor(utils.encode_cursor(utils.format_cursor(self.direction, self.cursor_value)))


class EncodedCursor(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any):
        if isinstance(v, EncodedCursor):
            return v
        if isinstance(v, DecodedCursor):
            return v.encode_cursor()
        utils.parse_cursor(utils.decode_cursor(v))
        return cls(v)

    def decode_cursor(self) -> DecodedCursor:
        return DecodedCursor(*utils.parse_cursor(utils.decode_cursor(self)))


class Base64EncodedData(str):
    def decode_to_binary(self) -> bytes:
        try:
            return urlsafe_b64decode(self)
        except binascii.Error as _:
            ...
        raise ValueError("invalid data")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any):
        if isinstance(v, Base64EncodedData):
            return v
        if isinstance(v, RawBinaryData):
            return v.encode_to_b64encoded_data()
        if isinstance(v, bytes):
            return RawBinaryData(v).encode_to_b64encoded_data()
        return cls(v)


class RawBinaryData(bytes):
    def encode_to_b64encoded_data(self) -> Base64EncodedData:
        return urlsafe_b64encode(self).decode("utf-8")


class DataTypeString(str):
    valid_types = set(
        (
            "text/plain",
            "text/uri-list",
            "text/csv",
            "text/css",
            "text/html",
            "application/xhtml+xml",
            "image/png",
            "image/jpg",
            "image/jpeg",
            "image/gif",
            "image/svg+xml",
            "application/xml",
            "text/xml",
            "application/javascript",
            "application/json",
            "application/octet-stream",
        )
    )

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any):
        if v not in cls.valid_types:
            raise ValueError(f"invalid data type: {v}")
        return cls(v)
