from base64 import urlsafe_b64encode
from datetime import datetime

import freezegun
from docserver import models, utils
from fastapi import status


def test_create_item_fails_if_no_valid_token_provided(client, settings, factories, fixture_users, fixture_collections):
    query = factories.ItemCreateQueryFactory.build()
    response = client.post(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}/items", data=query
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_returns_404_if_no_such_collection(
    mocker, client, settings, factories, fixture_users, fixture_collections
):
    query = factories.ItemCreateQueryFactory.build()
    user_id = fixture_users['testuser'].id
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": f"userId:{user_id}"})
    cid = utils.gen_uuid()
    while cid in set(d.id for d in fixture_collections["testuser_collections"]):
        cid = utils.gen_uuid()
    response = client.post(
        f"{settings.API_V1_STR}/collections/{cid}/items",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_item(mocker, client, db, settings, factories, fixture_users, fixture_collections):

    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    user_id = fixture_users['testuser'].id
    collection = fixture_collections["testuser_collections"][0]
    collection_id = collection.id
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": f"userId:{user_id}"})
    target_id = "2123456789abcdefABCDEF"
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value=target_id)
    query = factories.ItemCreateQueryFactory.build()

    sess = db.sessionmaker()
    assert (
        sess.query(models.Item)
        .filter(models.Item.owner_id == user_id, models.Item.collection_id == collection_id)
        .first()
        is None
    )

    with freezegun.freeze_time(dt):
        response = client.post(
            f"{settings.API_V1_STR}/collections/{collection_id}/items",
            data=query,
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "id": target_id,
            "ownerId": user_id,
            "collectionId": collection_id,
            "dataType": query.data_type,
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
        }
        decode.assert_called_once_with("the_access_token", key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    x = (
        sess.query(models.Item)
        .filter(models.Item.owner_id == user_id, models.Item.collection_id == collection_id)
        .first()
    )

    assert x is not None
    assert x.data_type == query.data_type
    assert x.created_at == dt
    assert x.updated_at == dt
    assert x.owner_id == user_id
    assert x.collection_id == collection_id
    assert x.id == target_id
    assert urlsafe_b64encode(x.body).decode("utf-8") == query.body
    sess.close()


def test_update_item_fails_if_no_valid_token_provided(
    client, settings, factories, fixture_users, fixture_collections, fixture_items
):
    query = factories.ItemUpdateQueryFactory.build()
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    response = client.put(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}/items/{item.id}",
        data=query,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_item(mocker, db, client, settings, factories, fixture_users, fixture_collections, fixture_items):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    sess = db.sessionmaker()
    query = factories.ItemUpdateQueryFactory.build(data_type="text/plain", body=b"updated")
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    dt = datetime(2022, 6, 23, 12, 23, 34, 5678)
    with freezegun.freeze_time(dt):
        response = client.put(
            f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
            data=query,
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "id": item.id,
            "ownerId": item.owner_id,
            "collectionId": item.collection_id,
            "dataType": query.data_type,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": dt.isoformat(),
        }
    x = sess.query(models.Item).get(item.id)
    assert x.data_type == query.data_type
    assert x.created_at == item.created_at
    assert x.updated_at == dt
    assert urlsafe_b64encode(x.body).decode("utf-8") == query.body


def test_update_item_returns_404_if_no_such_item(
    mocker, client, settings, factories, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    query = factories.ItemUpdateQueryFactory.build()
    collection = fixture_collections["testuser_collections"][0]
    iid = utils.gen_uuid()
    while iid in set(d.id for d in fixture_items["testuser_items"][collection.id]):
        iid = utils.gen_uuid()
    response = client.put(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{iid}",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_item_returns_404_if_other_users_item(
    mocker, client, settings, factories, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    query = factories.ItemUpdateQueryFactory.build()
    collection = fixture_collections["testuser2_collections"][0]
    item = fixture_items["testuser2_items"][collection.id][0]
    response = client.put(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_item_returns_404_if_other_collections_item(
    mocker, client, settings, factories, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    query = factories.ItemUpdateQueryFactory.build()
    collection = fixture_collections["testuser_collections"][0]
    other_collection = fixture_collections["testuser_collections"][1]
    item = fixture_items["testuser_items"][other_collection.id][0]
    response = client.put(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        data=query,
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_item_fails_if_no_valid_token_provided(client, settings, fixture_collections, fixture_items):
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_item(mocker, client, settings, fixture_users, fixture_collections, fixture_items):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": item.id,
        "ownerId": item.owner_id,
        "collectionId": item.collection_id,
        "dataType": item.data_type,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
        "body": 'YWFh',
    }


def test_retrieve_item_returns_404_if_no_such_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    iid = utils.gen_uuid()
    while iid in set(d.id for d in fixture_items["testuser_items"][collection.id]):
        iid = utils.gen_uuid()
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{iid}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_item_returns_404_if_other_users_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser2_collections"][0]
    item = fixture_items["testuser2_items"][collection.id][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_item_returns_404_if_other_collections_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    other_collection = fixture_collections["testuser_collections"][1]
    item = fixture_items["testuser_items"][other_collection.id][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_item_fails_if_no_valid_token_provided(
    client, settings, fixture_users, fixture_collections, fixture_items
):
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{fixture_collections['testuser_collections'][0].id}/items/{item.id}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_item(mocker, db, client, settings, factories, fixture_users, fixture_collections, fixture_items):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    sess = db.sessionmaker()
    collection = fixture_collections["testuser_collections"][0]
    item = fixture_items["testuser_items"][collection.id][0]
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert sess.query(models.Item).get(item.id) is None


def test_delete_item_returns_404_if_no_such_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    iid = utils.gen_uuid()
    while iid in set(d.id for d in fixture_items["testuser_items"][collection.id]):
        iid = utils.gen_uuid()
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{iid}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_item_returns_404_if_other_users_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser2_collections"][0]
    item = fixture_items["testuser2_items"][collection.id][0]
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_item_returns_404_if_other_collections_item(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    other_collection = fixture_collections["testuser_collections"][1]
    item = fixture_items["testuser_items"][other_collection.id][0]
    response = client.delete(
        f"{settings.API_V1_STR}/collections/{collection.id}/items/{item.id}",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_items_fails_if_no_valid_token_provided(client, settings, fixture_collections, fixture_items):
    collection = fixture_collections["testuser_collections"][0]
    response = client.get(f"{settings.API_V1_STR}/collections/{collection.id}/items")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_items_returns_404_if_other_users_collection(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    user = fixture_users['testuser']
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": f"userId:{user.id}"})
    collection = fixture_collections["testuser2_collections"][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_items_returns_404_if_no_such_collection(
    mocker, client, settings, fixture_users, fixture_collections, fixture_items
):
    user = fixture_users['testuser']
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": f"userId:{user.id}"})
    collection = fixture_collections["testuser2_collections"][0]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items",
        headers={"Authorization": "Bearer the_access_token"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_items_returns_empty(mocker, client, settings, fixture_users, fixture_collections):
    user = fixture_users["testuser"]
    decode = mocker.patch("docserver.operators.jwt.decode", return_value={"sub": f"userId:{user.id}"})
    collection = fixture_collections["testuser_collections"][-1]
    response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items", headers={"Authorization": "Bearer the_access_token"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"meta": {"count": 0, "nextCursor": None, "prevCursor": None}, "results": []}


def test_list_items_iterate_all(mocker, client, settings, fixture_users, fixture_collections, fixture_items):
    decode = mocker.patch(
        "docserver.operators.jwt.decode", return_value={"sub": f"userId:{fixture_users['testuser'].id}"}
    )
    collection = fixture_collections["testuser_collections"][0]
    items = fixture_items["testuser_items"][collection.id]
    first_response = client.get(
        f"{settings.API_V1_STR}/collections/{collection.id}/items",
        headers={"Authorization": "Bearer the_access_token"},
    )
    first_response_json = first_response.json()
    results = first_response_json["results"]
    next_cursor = first_response_json["meta"]["nextCursor"]
    assert first_response_json["meta"]["nextCursor"] is not None
    assert first_response_json["meta"]["prevCursor"] is None
    assert first_response.status_code == status.HTTP_200_OK

    last_prev_cursor = None
    last_result = []
    while next_cursor is not None:
        response = client.get(
            f"{settings.API_V1_STR}/collections/{collection.id}/items?cursor={next_cursor}",
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
            "collectionId": d.collection_id,
            "dataType": d.data_type,
            "updatedAt": d.updated_at.isoformat(),
            "createdAt": d.created_at.isoformat(),
            "ownerId": d.owner_id,
        }
        for d in sorted(items, key=lambda d: d.cursor_value, reverse=True)
    ]
    results = last_result
    prev_cursor = last_prev_cursor
    while prev_cursor is not None:
        response = client.get(
            f"{settings.API_V1_STR}/collections/{collection.id}/items?cursor={prev_cursor}",
            headers={"Authorization": "Bearer the_access_token"},
        )
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        results = response_json["results"] + results
        prev_cursor = response_json["meta"]["prevCursor"]
    assert results == [
        {
            "id": d.id,
            "collectionId": d.collection_id,
            "dataType": d.data_type,
            "updatedAt": d.updated_at.isoformat(),
            "createdAt": d.created_at.isoformat(),
            "ownerId": d.owner_id,
        }
        for d in sorted(items, key=lambda d: d.cursor_value, reverse=True)
    ]
