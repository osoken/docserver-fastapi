import re
from datetime import datetime, timedelta
import freezegun
from docserver import utils


def test_gen_uuid():
    actual = [utils.gen_uuid() for _ in range(1000)]
    assert len(set(actual)) == 1000
    assert len(set(len(d) for d in actual)) == 1
    assert all(len(d) == utils.suuid_generator.encoded_length() for d in actual)
    assert all(re.match(r"^[a-zA-Z0-9]+$", d) for d in actual)


def test_gen_datetime(mocker):
    m = mocker.patch("docserver.utils.datetime")
    actual = utils.gen_datetime()
    assert actual == m.utcnow.return_value
