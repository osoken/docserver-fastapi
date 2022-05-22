import json
from datetime import datetime

import freezegun


def test_create_user(mocker, client, factories):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value="0123456789abcdefABCDEF")

    with freezegun.freeze_time(dt):
        query = factories.UserCreateQueryFactory.build()
        response = client.post(
            "/api/v1/users",
            json=query.dict(),
        )
        assert response.status_code == 200
        assert response.json() == {
            "username": query.username,
            "email": query.email,
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
            "id": "0123456789abcdefABCDEF",
        }
