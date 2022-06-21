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
        return DecodedCursor(utils.parse_cursor(utils.decode_cursor(self)))
