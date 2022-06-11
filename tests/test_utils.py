import pytest
from docserver import utils


def test_gen_uuid():
    actual = [utils.gen_uuid() for _ in range(1000)]
    assert len(set(actual)) == 1000
    assert len(set(len(d) for d in actual)) == 1
    assert len(actual[0]) == utils.suuid_generator.encoded_length()
