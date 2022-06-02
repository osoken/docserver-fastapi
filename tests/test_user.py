from datetime import datetime, timedelta
from unittest.mock import call

import freezegun
from docserver import models
from fastapi import status
from jose.exceptions import ExpiredSignatureError


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


def test_get_token_with_generated_refresh_token(mocker, settings, db, client, factories, fixture_users):
    m = mocker.patch("docserver.operators.jwt.encode", side_effect=["the_access_token", "the_refresh_token"])
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="p@ssW0rd")
    with freezegun.freeze_time(dt):
        response = client.post(
            settings.API_V1_STR + "/token",
            data=query,
        )
        assert response.status_code == status.HTTP_200_OK
        res_json = response.json()
        assert res_json["tokenType"] == "bearer"
        assert res_json["accessToken"] == "the_access_token"
        assert res_json["refreshToken"] == "the_refresh_token"
        m.assert_has_calls(
            [
                call(
                    {
                        "sub": "userId:0123456789abcdefABCDEF",
                        "exp": dt + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                    },
                    key=settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM,
                )
            ],
            [
                call(
                    {
                        "sub": "userId:0123456789abcdefABCDEF",
                        "exp": dt + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
                    },
                    key=settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM,
                )
            ],
        )
        sess = db.sessionmaker()
        x = sess.query(models.RefreshToken).filter_by(user_id="0123456789abcdefABCDEF").one()
        assert x.token == "the_refresh_token"
        assert x.created_at == dt
        assert x.updated_at == dt
        sess.close()


def test_get_token_with_stored_refresh_token(mocker, settings, client, factories, fixture_refresh_token):
    encode = mocker.patch("docserver.operators.jwt.encode", return_value="the_access_token")
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": "userId:0123456789abcdefABCDEF"})
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="p@ssW0rd")
    with freezegun.freeze_time(dt):
        response = client.post(
            settings.API_V1_STR + "/token",
            data=query,
        )
        assert response.status_code == status.HTTP_200_OK
        res_json = response.json()
        assert res_json["tokenType"] == "bearer"
        assert res_json["accessToken"] == "the_access_token"
        assert res_json["refreshToken"] == "the_refresh_token"
        encode.assert_called_once_with(
            {
                "sub": "userId:0123456789abcdefABCDEF",
                "exp": dt + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            },
            key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        decode.assert_called_once_with("the_refresh_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_get_token_with_stored_but_old_refresh_token(mocker, settings, db, client, factories, fixture_refresh_token):
    def raise_expired_signature_error(*args, **kwargs):
        raise ExpiredSignatureError

    encode = mocker.patch(
        "docserver.operators.jwt.encode", side_effect=["the_access_token", "the_regenerated_refresh_token"]
    )
    decode = mocker.patch("docserver.operators.jwt.decode", side_effect=raise_expired_signature_error)
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="p@ssW0rd")
    with freezegun.freeze_time(dt):
        response = client.post(
            settings.API_V1_STR + "/token",
            data=query,
        )
        assert response.status_code == status.HTTP_200_OK
        res_json = response.json()
        assert res_json["tokenType"] == "bearer"
        assert res_json["accessToken"] == "the_access_token"
        assert res_json["refreshToken"] == "the_regenerated_refresh_token"
        encode.assert_has_calls(
            [
                call(
                    {
                        "sub": "userId:0123456789abcdefABCDEF",
                        "exp": dt + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                    },
                    key=settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM,
                )
            ],
            [
                call(
                    {
                        "sub": "userId:0123456789abcdefABCDEF",
                        "exp": dt + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
                    },
                    key=settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM,
                )
            ],
        )
        decode.assert_called_once_with("the_refresh_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sess = db.sessionmaker()
        x = sess.query(models.RefreshToken).filter_by(user_id="0123456789abcdefABCDEF").one()
        assert x.token == "the_regenerated_refresh_token"
        assert x.created_at != dt
        assert x.updated_at == dt
        sess.close()


def test_get_token_fails_when_wrong_password(client, settings, factories, fixture_users):
    query = factories.UserLoginQueryFactory.build(login_id="testuser", password="wr0ngP@ssWord")
    response = client.post(
        settings.API_V1_STR + "/token",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_recreate_access_token(mocker, client, settings, factories, fixture_refresh_token):
    encode = mocker.patch("docserver.operators.jwt.encode", return_value="the_access_token")
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": "userId:0123456789abcdefABCDEF"})
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    with freezegun.freeze_time(dt):
        response = client.get(settings.API_V1_STR + "/token/refresh", headers={"Authorization": "the_refresh_token"})
        assert response.status_code == status.HTTP_200_OK
        res_json = response.json()
        assert res_json["accessToken"] == "the_access_token"
        encode.assert_has_calls(
            [
                call(
                    {
                        "sub": "userId:0123456789abcdefABCDEF",
                        "exp": dt + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                    },
                    key=settings.SECRET_KEY,
                    algorithm=settings.ALGORITHM,
                )
            ],
        )
        decode.assert_called_once_with("the_refresh_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
