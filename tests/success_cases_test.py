from dataclasses import dataclass

import pytest

from src.pserialize import MissingRequiredFieldException, deserialize, serialize
from src.pserialize.deserialize import DeserializeClassException

from .models.enum import Number


@dataclass
class Child:
    count: int


@dataclass
class Parent:
    children: list[Child]
    lookup: dict[str, Child]
    number: Number


def test_nested_list_dict_and_enum_round_trip():
    value = Parent(
        children=[Child(1), Child(2)],
        lookup={"first": Child(1), "second": Child(2)},
        number=Number.THREE,
    )

    serialized = serialize(value)
    deserialized = deserialize(serialized, Parent)

    assert serialized == {
        "children": [{"count": 1}, {"count": 2}],
        "lookup": {
            "first": {"count": 1},
            "second": {"count": 2},
        },
        "number": "three",
    }
    assert deserialized == value


def test_missing_required_fields_are_rejected():
    @dataclass
    class User:
        id: int
        name: str

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"id": 1}, User)

    assert isinstance(captured.value.error, MissingRequiredFieldException)
    assert captured.value.error.field_name == "name"


def test_strict_mode_ignores_extra_fields():
    @dataclass
    class User:
        id: int

    deserialized = deserialize({"id": 1, "extra": "ignored"}, User, strict=True)

    assert deserialized.id == 1
    assert not hasattr(deserialized, "extra")
