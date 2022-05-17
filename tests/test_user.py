import json
from datetime import datetime

import freezegun


def test_create_user(mocker, client):
    dt = datetime(2021, 1, 31, 12, 23, 34, 5678)
    mocker.patch("docserver.utils.suuid_generator.uuid", return_value="0123456789abcdefABCDEF")

    with freezegun.freeze_time(dt):
        response = client.post(
            "/api/v1/users",
            data=json.dumps({"username": "test", "email": "some@valid.email.com", "password": "Tes+U5er!@#"}),
        )
        assert response.status_code == 200
        assert response.json() == {
            "username": "test",
            "email": "some@valid.email.com",
            "createdAt": dt.isoformat(),
            "updatedAt": dt.isoformat(),
            "id": "0123456789abcdefABCDEF",
        }
