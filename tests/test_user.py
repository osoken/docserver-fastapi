from datetime import datetime, timedelta

import freezegun
from fastapi import status


def test_create_user(mocker, client, factories):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value="0123456789abcdefABCDEF")

    with freezegun.freeze_time(dt):
        query = factories.UserCreateQueryFactory.build()
        response = client.post(
            "/api/v1/users",
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


def test_create_user_fails_if_username_already_exists(client, factories, fixture_users):
    query = factories.UserCreateQueryFactory.build(username="testuser", email="test@anywhere.com")
    response = client.post(
        "/api/v1/users",
        data=query,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "username and/or email already exists."}


def test_create_user_fails_if_email_already_exists(client, factories, fixture_users):
    query = factories.UserCreateQueryFactory.build(username="testuser2", email="test@somewhere.com")
    response = client.post(
        "/api/v1/users",
        data=query,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "username and/or email already exists."}


def test_get_token(mocker, settings, client, factories, fixture_users):
    m = mocker.patch("docserver.operators.jwt.encode", return_value="the token")
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="p@ssW0rd")
    with freezegun.freeze_time(dt):
        response = client.post(
            "/api/v1/token",
            data=query,
        )
        assert response.status_code == status.HTTP_200_OK
        res_json = response.json()
        assert res_json["tokenType"] == "bearer"
        assert res_json["accessToken"] == m.return_value
        m.assert_called_once_with(
            {
                "sub": "userId:0123456789abcdefABCDEF",
                "exp": dt + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )


def test_get_token_fails_when_wrong_password(client, factories, fixture_users):
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="wr0ngP@ssWord")
    response = client.post(
        "/api/v1/token",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
