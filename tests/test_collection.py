from base64 import encode
from datetime import datetime
from unittest.mock import MagicMock, call

import freezegun
from docserver import models, types, utils
from fastapi import status


def test_create_collection_fails_if_no_valid_token_provided(client, settings, factories, fixture_users):
    query = factories.CollectionCreateQueryFactory.build()
    response = client.post(
        settings.API_V1_STR + "/collections",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_collections(mocker, db, client, factories, settings, fixture_users):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    target_id = "2123456789abcdefABCDEF"
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value=target_id)
    query = factories.CollectionCreateQueryFactory.build()

    sess = db.sessionmaker()
    assert sess.query(models.Collection).get(target_id) is None

    with freezegun.freeze_time(dt):
        response = client.post(
            settings.API_V1_STR + "/collections", data=query, headers={"Authorization": "Bearer the_access_token"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "name": query.name,
            "ownerId": fixture_users["testuser"].id,
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
            "id": target_id,
        }
        decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    x = sess.query(models.Collection).get(target_id)
    assert x is not None
    assert x.name == query.name
    assert x.created_at == dt
    assert x.updated_at == dt
    assert x.owner_id == fixture_users["testuser"].id
    sess.close()


def test_list_collection_fails_if_no_valid_token_provided(client, settings, fixture_collections):
    response = client.get(f"{settings.API_V1_STR}/collections")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_collection_returns_empty_if_user_has_no_collection(mocker, client, settings, fixture_users):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.get(f"{settings.API_V1_STR}/collections", headers={"Authorization": "Bearer the_access_token"})
    assert response.status_code == status.HTTP_200_OK
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert response.json() == {
        "meta": {
            "count": 0,
            "nextCursor": None,
            "prevCursor": None,
        },
        "results": [],
    }


def test_list_collection_returns_first_ten_collections(mocker, client, settings, fixture_users, fixture_collections):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    mocker.patch("docserver.types.DecodedCursor.encode_cursor", return_value="the_next_cursor")
    DecodedCursor_init = mocker.patch("docserver.types.DecodedCursor.__init__", return_value=None)
    response = client.get(f"{settings.API_V1_STR}/collections", headers={"Authorization": "Bearer the_access_token"})

    assert response.status_code == status.HTTP_200_OK
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    DecodedCursor_init.assert_called_once_with("n", fixture_collections["testuser_collections"][-11].cursor_value)
    assert response.json() == {
        "meta": {
            "count": 123,
            "nextCursor": "the_next_cursor",
            "prevCursor": None,
        },
        "results": [
            {
                "id": d.id,
                "name": d.name,
                "updatedAt": d.updated_at.isoformat(),
                "createdAt": d.created_at.isoformat(),
                "ownerId": d.owner_id,
            }
            for d in fixture_collections["testuser_collections"][-1:-11:-1]
        ],
    }


def test_list_collection_returns_next_ten_collections_with_next_cursor(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    cursor = MagicMock(spec=types.DecodedCursor)
    cursor.direction = "n"
    cursor.cursor_value = fixture_collections["testuser_collections"][-11].cursor_value
    mocker.patch("docserver.types.DecodedCursor.encode_cursor", side_effect=["the_next_next_cursor", "the_prev_cursor"])
    mocker.patch("docserver.types.EncodedCursor.decode_cursor", return_value=cursor)
    mocker.patch("docserver.utils.decode_cursor")
    mocker.patch("docserver.utils.parse_cursor")
    DecodedCursor_init = mocker.patch("docserver.types.DecodedCursor.__init__", return_value=None)

    response = client.get(
        f"{settings.API_V1_STR}/collections?cursor=the_next_cursor",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    DecodedCursor_init.assert_has_calls(
        [
            call("n", fixture_collections["testuser_collections"][-21].cursor_value),
            call("p", fixture_collections["testuser_collections"][-10].cursor_value),
        ]
    )
    assert response.json() == {
        "meta": {
            "count": 123,
            "nextCursor": "the_next_next_cursor",
            "prevCursor": "the_prev_cursor",
        },
        "results": [
            {
                "id": d.id,
                "name": d.name,
                "updatedAt": d.updated_at.isoformat(),
                "createdAt": d.created_at.isoformat(),
                "ownerId": d.owner_id,
            }
            for d in fixture_collections["testuser_collections"][-11:-21:-1]
        ],
    }


def test_list_collection_returns_previous_ten_collections_with_prev_cursor(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    cursor = MagicMock(spec=types.DecodedCursor)
    cursor.direction = "p"
    cursor.cursor_value = fixture_collections["testuser_collections"][-31].cursor_value
    mocker.patch("docserver.types.DecodedCursor.encode_cursor", side_effect=["the_next_cursor", "the_prev_prev_cursor"])
    mocker.patch("docserver.types.EncodedCursor.decode_cursor", return_value=cursor)
    mocker.patch("docserver.utils.decode_cursor")
    mocker.patch("docserver.utils.parse_cursor")
    DecodedCursor_init = mocker.patch("docserver.types.DecodedCursor.__init__", return_value=None)

    response = client.get(
        f"{settings.API_V1_STR}/collections?cursor=the_prev_cursor",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    DecodedCursor_init.assert_has_calls(
        [
            call("n", fixture_collections["testuser_collections"][-32].cursor_value),
            call("p", fixture_collections["testuser_collections"][-21].cursor_value),
        ]
    )
    assert response.json() == {
        "meta": {
            "count": 123,
            "nextCursor": "the_next_cursor",
            "prevCursor": "the_prev_prev_cursor",
        },
        "results": [
            {
                "id": d.id,
                "name": d.name,
                "updatedAt": d.updated_at.isoformat(),
                "createdAt": d.created_at.isoformat(),
                "ownerId": d.owner_id,
            }
            for d in fixture_collections["testuser_collections"][-22:-32:-1]
        ],
    }


def test_list_collection_iterate_all(mocker, client, settings, fixture_users, fixture_collections):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    first_response = client.get(
        f"{settings.API_V1_STR}/collections",
        headers={"Authorization": "Bearer the_access_token"},
    )
    first_response_json = first_response.json()
    results = first_response_json["results"]
    next_cursor = first_response_json["meta"]["nextCursor"]
    assert first_response_json["meta"]["prevCursor"] is None
    assert first_response.status_code == status.HTTP_200_OK
    decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    last_prev_cursor = None
    while next_cursor is not None:
        response = client.get(
            f"{settings.API_V1_STR}/collections?cursor={next_cursor}",
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        results += response_json["results"]
        next_cursor = response_json["meta"]["nextCursor"]
        last_prev_cursor = response_json["meta"]["prevCursor"]
        last_result = response_json["results"]
    assert results == [
        {
            "id": d.id,
            "name": d.name,
            "updatedAt": d.updated_at.isoformat(),
            "createdAt": d.created_at.isoformat(),
            "ownerId": d.owner_id,
        }
        for d in sorted(fixture_collections["testuser_collections"], key=lambda d: d.cursor_value, reverse=True)
    ]
    results = last_result
    prev_cursor = last_prev_cursor
    while prev_cursor is not None:
        response = client.get(
            f"{settings.API_V1_STR}/collections?cursor={prev_cursor}",
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        results = response_json["results"] + results
        prev_cursor = response_json["meta"]["prevCursor"]
    assert results == [
        {
            "id": d.id,
            "name": d.name,
            "updatedAt": d.updated_at.isoformat(),
            "createdAt": d.created_at.isoformat(),
            "ownerId": d.owner_id,
        }
        for d in sorted(fixture_collections["testuser_collections"], key=lambda d: d.cursor_value, reverse=True)
    ]


def test_retrieve_collection_fails_if_no_valid_token_provided(client, settings, factories, fixture_collections):
    response = client.get(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_collection(mocker, client, settings, fixture_users, fixture_collections):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.get(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][12].id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    expected = fixture_collections['testuser_collections'][12]
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": expected.id,
        "name": expected.name,
        "updatedAt": expected.updated_at.isoformat(),
        "createdAt": expected.created_at.isoformat(),
        "ownerId": expected.owner_id,
    }


def test_retrieve_collection_returns_404_if_no_such_collection(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    cid = utils.gen_uuid()
    while cid in set(d.id for d in fixture_collections["testuser_collections"]):
        cid = utils.gen_uuid()
    response = client.get(
        f"{settings.API_V1_STR}/collections/{cid}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_collection_returns_404_if_other_users_collection(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.get(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser2_collections'][1].id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_collection_fails_if_no_valid_token_provided(client, settings, factories, fixture_collections):
    query = factories.CollectionUpdateQueryFactory.build()
    response = client.put(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_collection(mocker, db, client, settings, factories, fixture_users, fixture_collections):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    expected = fixture_collections['testuser_collections'][12]
    query = factories.CollectionUpdateQueryFactory.build(name=f"updated_{expected.name}")
    sess = db.sessionmaker()
    x0 = sess.query(models.Collection).get(expected.id)
    before_cursor = x0.cursor_value
    assert x0.name != query.name
    dt = datetime(2023, 1, 31, 12, 23, 34, 5678)
    with freezegun.freeze_time(dt):
        response = client.put(
            f"{settings.API_V1_STR}/collections/{expected.id}",
            data=query,
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "id": expected.id,
            "name": query.name,
            "updatedAt": dt.isoformat(),
            "createdAt": expected.created_at.isoformat(),
            "ownerId": expected.owner_id,
        }
    sess.refresh(x0)
    assert x0.name == query.name
    assert x0.updated_at == dt
    assert x0.cursor_value != before_cursor
    sess.close()


def test_update_collection_returns_404_if_no_such_collection(
    mocker, client, settings, factories, fixture_users, fixture_collections
):
    query = factories.CollectionUpdateQueryFactory.build()

    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    cid = utils.gen_uuid()
    while cid in set(d.id for d in fixture_collections["testuser_collections"]):
        cid = utils.gen_uuid()
    response = client.put(
        f"{settings.API_V1_STR}/collections/{cid}",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_collection_returns_404_if_other_users_collection(
    mocker, client, settings, factories, fixture_users, fixture_collections
):
    query = factories.CollectionUpdateQueryFactory.build()
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.put(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser2_collections'][1].id}",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_collection_fails_if_no_valid_token_provided(client, settings, fixture_collections):
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_collection(mocker, db, client, settings, fixture_users, fixture_collections):
    target_id = fixture_collections['testuser_collections'][12].id
    sess = db.sessionmaker()
    assert sess.query(models.Collection).get(target_id) is not None
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{target_id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert sess.query(models.Collection).get(target_id) is None
    sess.close()


def test_delete_collection_returns_404_if_no_such_collection(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    cid = utils.gen_uuid()
    while cid in set(d.id for d in fixture_collections["testuser_collections"]):
        cid = utils.gen_uuid()
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{cid}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_collection_returns_404_if_other_users_collection(
    mocker, client, settings, fixture_users, fixture_collections
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser2_collections'][1].id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
