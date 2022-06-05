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
