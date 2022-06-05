from datetime import datetime

import freezegun
from fastapi import status


def test_create_user(mocker, client, factories, settings):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value="0123456789abcdefABCDEF")

    with freezegun.freeze_time(dt):
        query = factories.UserCreateQueryFactory.build()
        response = client.post(
            settings.API_V1_STR + "/users",
            data=query,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "username": query.username,
            "email": query.email,
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
            "id": "0123456789abcdefABCDEF",
        }


def test_create_user_fails_if_username_already_exists(client, settings, factories, fixture_users):
    query = factories.UserCreateQueryFactory.build(username="testuser", email="test@anywhere.com")
    response = client.post(
        settings.API_V1_STR + "/users",
        data=query,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "username and/or email already exists."}


def test_create_user_fails_if_email_already_exists(client, settings, factories, fixture_users):
    query = factories.UserCreateQueryFactory.build(username="testuser2", email="test@somewhere.com")
    response = client.post(
        settings.API_V1_STR + "/users",
        data=query,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "username and/or email already exists."}


def test_get_user_info_fails_if_no_valid_token_provided(client, settings, fixture_users):
    response = client.get(settings.API_V1_STR + "/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_user_info(mocker, client, settings, fixture_users):
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": "userId:0123456789abcdefABCDEF"})
    response = client.get(settings.API_V1_STR + "/users/me", headers={"Authorization": "Bearer the_access_token"})
    assert response.status_code == status.HTTP_200_OK
    res_json = response.json()
    assert res_json == {
        "id": "0123456789abcdefABCDEF",
        "username": "testuser",
        "email": "test@somewhere.com",
        "createdAt": datetime(2022, 6, 5, 14, 51, 35).isoformat(),
        "updatedAt": datetime(2022, 6, 9, 12, 11, 15).isoformat(),
    }
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
