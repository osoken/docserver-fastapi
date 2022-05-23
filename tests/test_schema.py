from multiprocessing.sharedctypes import Value

import pytest
from docserver import schema


@pytest.mark.parametrize(
    ["username", "expected_as_valid"],
    [
        ["0", False],
        ["a12", True],
        ["0000123", False],
        ["abby", True],
        ["takeshi@", False],
        ["a0000123", True],
        ["__private", False],
        ["__magic__", False],
        ["ab", False],
        ["a-_", True],
        ["toooooooooooooooooooooooooo_long", False],
        ["v012345678901234567890123456789", True],
        ["", False],
    ],
)
def test_user_create_query_username_validation(username: str, expected_as_valid: bool):
    try:
        sut = schema.UserCreateQuery(username=username, email="some@valid.email.com", password="S0me_S+r0n9_P@ss")
        assert sut.username == username
    except ValueError as _:
        assert not expected_as_valid


@pytest.mark.parametrize(
    ["password", "expected_as_valid"],
    [
        ["", False],
        ["  ", False],
        ["1aA!", False],
        ["1aA!1aA!", True],
        ["1aa!1aa!", False],
        ["aaA!aaA!", False],
        ["1aA01aA0", False],
        ["1aA!1aA!0123", True],
        ["S0me_S+r0n9_P@ss", True],
        ["S+r0n9but_tooooooooooooooooo_long", False],
        ["S+r0n9and_enoooooooooooough_long", True],
    ],
)
def test_user_create_query_password_validation(password: str, expected_as_valid: bool):
    from pydantic import SecretStr

    try:
        sut = schema.UserCreateQuery(username="valid_username", email="some@valid.email.com", password=password)
        assert sut.password == SecretStr(value=password)
    except ValueError as _:
        assert not expected_as_valid


@pytest.mark.parametrize(
    ["login_id", "expected_as"], [["username", "username"], ["email@address.com", "email"], ["00invalid", "invalid"]]
)
def test_user_login_query_login_id_validation(login_id: str, expected_as: str):
    try:
        sut = schema.UserLoginQuery(login_id=login_id, password="s0meP@ssword")
        if expected_as == "username":
            schema.UsernameString.validate(value=login_id)
            assert sut.is_username()
            assert not sut.is_email()
        elif expected_as == "email":
            schema.EmailStr.validate(value=login_id)
            assert not sut.is_username()
            assert sut.is_email()
        else:
            assert False
    except ValueError as _:
        assert expected_as == "invalid"
