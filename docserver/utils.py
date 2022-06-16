import hashlib
from datetime import datetime
from random import choices, shuffle
from string import ascii_lowercase, ascii_uppercase, digits

import shortuuid

suuid_generator = shortuuid.ShortUUID()
suuid_generator.set_alphabet("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def calc_hash(x: bytes):
    m = hashlib.md5()
    m.update(x)
    return m.hexdigest()


def gen_uuid() -> str:
    return suuid_generator.uuid()


def gen_datetime() -> datetime:
    return datetime.utcnow()


def format_timestamp(dt: datetime) -> str:
    return f"{int(dt.timestamp() * 1000)}"


def format_cursor_value(dt: datetime, id_str: str) -> str:
    return f"{format_timestamp(dt)}|{id_str}"


symbols = "`~!@#$%^&*()-_+={[]|:;\"'<,>.?/}"
all_chars = ascii_lowercase + ascii_uppercase + digits + symbols


def gen_password(length: int) -> str:
    if length < 8 or length > 32:
        raise ValueError('length must be more than 8 and less than 32')
    l2 = choices(ascii_lowercase, k=1)
    u2 = choices(ascii_uppercase, k=1)
    d2 = choices(digits, k=1)
    s2 = choices(symbols, k=1)
    others = choices(all_chars, k=length - 4)
    chars = l2 + u2 + d2 + s2 + others
    shuffle(chars)
    return "".join(chars)
