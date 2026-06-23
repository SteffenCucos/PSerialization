from dataclasses import dataclass

from src.pserialize import deserialize, serialize


def test_tuple_round_trip_with_fixed_types():
    value = (1, "two", 3.0)

    serialized = serialize(value)
    deserialized = deserialize(serialized, tuple[int, str, float])

    assert serialized == [1, "two", 3.0]
    assert deserialized == value


def test_tuple_round_trip_with_repeated_type():
    value = (1, 2, 3)

    serialized = serialize(value)
    deserialized = deserialize(serialized, tuple[int, ...])

    assert serialized == [1, 2, 3]
    assert deserialized == value


def test_set_round_trip():
    value = {1, 2, 3}

    serialized = serialize(value)
    deserialized = deserialize(serialized, set[int])

    assert sorted(serialized) == [1, 2, 3]
    assert deserialized == value


def test_frozenset_round_trip():
    value = frozenset(["a", "b", "c"])

    serialized = serialize(value)
    deserialized = deserialize(serialized, frozenset[str])

    assert sorted(serialized) == ["a", "b", "c"]
    assert deserialized == value


def test_dataclass_with_collection_fields_round_trip():
    @dataclass
    class Inventory:
        names: tuple[str, ...]
        ids: set[int]
        tags: frozenset[str]

    value = Inventory(("one", "two"), {1, 2}, frozenset(["active", "test"]))

    serialized = serialize(value)
    deserialized = deserialize(serialized, Inventory)

    assert serialized["names"] == ["one", "two"]
    assert sorted(serialized["ids"]) == [1, 2]
    assert sorted(serialized["tags"]) == ["active", "test"]
    assert deserialized == value


def test_tuple_length_mismatch_raises_deserialization_error():
    error = None

    try:
        deserialize([1, 2], tuple[int, str, float])
    except Exception as e:
        error = e

    assert error is not None
    assert "Expected tuple of length 3, got 2" in str(error)
