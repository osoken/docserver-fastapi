import hashlib
from datetime import datetime

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
