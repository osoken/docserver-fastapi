import re
from datetime import datetime, timedelta

import freezegun
import pytest
from docserver import utils


def test_gen_uuid():
    actual = [utils.gen_uuid() for _ in range(1000)]
    assert len(set(actual)) == 1000
    assert len(set(len(d) for d in actual)) == 1
    assert all(len(d) == utils.suuid_generator.encoded_length() for d in actual)
    assert all(re.match(r"^[a-zA-Z0-9]+$", d) for d in actual)


def test_gen_datetime(mocker):
    m = mocker.patch("docserver.utils.datetime")
    actual = utils.gen_datetime()
    assert actual == m.utcnow.return_value


def test_format_timestamp():
    ts = 1655213261.556825
    dt = datetime.fromtimestamp(ts)
    actual = utils.format_timestamp(dt)
    expected = "1655213261556825"
    assert actual == expected


def test_format_cursor_value():
    id_ = "0123456789abcdefABCDEF"
    ts = 1655213261.556825
    dt = datetime.fromtimestamp(ts)
    actual = utils.format_cursor_value(dt, id_)
    expected = "1655213261556825|0123456789abcdefABCDEF"
    assert actual == expected


def test_gen_password_raises_value_error_when_given_length_is_too_short_or_too_long():
    with pytest.raises(ValueError):
        _ = utils.gen_password(7)
    with pytest.raises(ValueError):
        _ = utils.gen_password(33)


def test_gen_password():
    for i in range(8, 33):
        actual = utils.gen_password(i)
        assert len(actual) == i
        assert re.match(".*[0-9].*", actual) is not None
        assert re.match(".*[a-z].*", actual) is not None
        assert re.match(".*[A-Z].*", actual) is not None
        assert re.match(f".*[{utils.symbols}].*", actual) is not None


def test_format_next_cursor():
    cursor_value = "1655213261556825|0123456789abcdefABCDEF"
    actual = utils.format_next_cursor(cursor_value)
    assert actual == "n|1655213261556825|0123456789abcdefABCDEF"


def test_format_prev_cursor():
    cursor_value = "1655213261556825|0123456789abcdefABCDEF"
    actual = utils.format_prev_cursor(cursor_value)
    assert actual == "p|1655213261556825|0123456789abcdefABCDEF"


def test_format_cursor():
    cursor_value = "1655213261556825|0123456789abcdefABCDEF"
    direction = "p"
    actual = utils.format_cursor(direction, cursor_value)
    assert actual == "p|1655213261556825|0123456789abcdefABCDEF"


def test_encode_cursor_next_cursor():
    cursor = "n|1655213261556825|0123456789abcdefABCDEF"
    actual = utils.encode_cursor(cursor)
    assert actual == "bnwxNjU1MjEzMjYxNTU2ODI1fDAxMjM0NTY3ODlhYmNkZWZBQkNERUY="


def test_encode_cursor_prev_cursor():
    cursor = "p|1655213261556825|0123456789abcdefABCDEF"
    actual = utils.encode_cursor(cursor)
    assert actual == "cHwxNjU1MjEzMjYxNTU2ODI1fDAxMjM0NTY3ODlhYmNkZWZBQkNERUY="


def test_decode_cursor():
    encoded_cursor = "cHwxNjU1MjEzMjYxNTU2ODI1fDAxMjM0NTY3ODlhYmNkZWZBQkNERUY="
    actual = utils.decode_cursor(encoded_cursor)
    assert actual == "p|1655213261556825|0123456789abcdefABCDEF"


def test_parse_cursor():
    decoded_cursor = "p|1655213261556825|0123456789abcdefABCDEF"
    actual = utils.parse_cursor(decoded_cursor)
    assert actual == ("p", "1655213261556825|0123456789abcdefABCDEF")
