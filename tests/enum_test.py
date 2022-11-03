import pytest

from src.pserialize.pserialize import serialize, deserialize

from .models.enum import Number


@pytest.mark.parametrize("input,expected", [
    (Number.ONE, "one"),
    ([Number.ONE, Number.TWO], ["one", "two"]),
    ({Number.FIVE: 5}, {"five": 5})
])
def test_serialize_enum(input, expected):
    assert serialize(input) == expected

@pytest.mark.parametrize("input,type,expected", [
    ("one", Number, Number.ONE),
    (["one", "two"], list[Number], [Number.ONE, Number.TWO]),
    ({"five": 5}, dict[Number,int], {Number.FIVE: 5})
])
def test_deserialize_enum(input, type, expected):
    assert deserialize(input, type) == expected

