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


def gen_timestamp() -> datetime:
    return datetime.utcnow()


symbols = "`~!@#$%^&*()-_+={[]|:;\"'<,>.?/}"
all_chars = ascii_lowercase + ascii_uppercase + digits + symbols


def gen_password(length: int) -> str:
    if length < 8 or length > 32:
        raise ValueError('length must be more than 8 and less than 32')
    l = choices(ascii_lowercase, k=2)
    u = choices(ascii_uppercase, k=2)
    d = choices(digits, k=2)
    s = choices(symbols, k=2)
    o = choices(all_chars, k=length - 8)
    chars = l + u + d + s + o
    shuffle(chars)
    return "".join(chars)
