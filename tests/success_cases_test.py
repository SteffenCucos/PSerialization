from dataclasses import dataclass

from src.pserialize import deserialize, serialize

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


def test_missing_fields_are_set_to_none():
    @dataclass
    class User:
        id: int
        name: str

    deserialized = deserialize({"id": 1}, User)

    assert deserialized.id == 1
    assert deserialized.name is None


def test_strict_mode_ignores_extra_fields():
    @dataclass
    class User:
        id: int

    deserialized = deserialize({"id": 1, "extra": "ignored"}, User, strict=True)

    assert deserialized.id == 1
    assert not hasattr(deserialized, "extra")
