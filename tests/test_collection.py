from datetime import datetime

import freezegun
from fastapi import status


def test_create_collection_fails_if_no_valid_token_provided(client, settings, factories, fixture_users):
    query = factories.CollectionCreateQueryFactory.build()
    response = client.post(
        settings.API_V1_STR + "/collections",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_collections(mocker, client, factories, settings, fixture_users):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value="2123456789abcdefABCDEF")

    with freezegun.freeze_time(dt):
        query = factories.CollectionCreateQueryFactory.build()
        response = client.post(
            settings.API_V1_STR + "/collections", data=query, headers={"Authorization": "Bearer the_access_token"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "name": query.name,
            "ownerId": fixture_users["testuser"].id,
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
            "id": "2123456789abcdefABCDEF",
        }
        decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_list_collection_fails_if_no_valid_token_provided(client, settings, fixture_collections):
    response = client.get(f"{settings.API_V1_STR}/collections")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
