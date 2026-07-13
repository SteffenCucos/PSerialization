from collections import OrderedDict

import pytest

from src.pserialize import (
    SerializedKeyCollisionException,
    UnsupportedKeyTypeException,
    serialize,
)


def test_string_dictionary_keys_are_preserved():
    assert serialize({"one": 1, "two": 2}) == {"one": 1, "two": 2}


@pytest.mark.parametrize("key", [1, True, 1.5, (1, 2)])
def test_non_string_dictionary_keys_are_rejected(key):
    with pytest.raises(UnsupportedKeyTypeException) as captured:
        serialize({key: "value"})

    assert captured.value.key_type is type(key)
    assert captured.value.serialized_key_type is None


def test_non_string_nested_dictionary_key_is_rejected():
    with pytest.raises(UnsupportedKeyTypeException):
        serialize({"outer": {1: "value"}})


def test_string_key_mapping_implementations_are_supported():
    mapping = OrderedDict([("first", 1), ("second", 2)])

    assert serialize(mapping) == {"first": 1, "second": 2}


def test_string_key_middleware_remains_supported():
    result = serialize(
        {"FIRST": "VALUE"},
        middleware={str: lambda value, _context: value.lower()},
    )

    assert result == {"first": "value"}


def test_key_middleware_must_return_a_string():
    with pytest.raises(UnsupportedKeyTypeException) as captured:
        serialize(
            {"key": "value"},
            middleware={str: lambda value, _context: [value]},
        )

    assert captured.value.key_type is str
    assert captured.value.serialized_key_type is list


def test_key_middleware_collisions_are_rejected():
    with pytest.raises(SerializedKeyCollisionException) as captured:
        serialize(
            {"FIRST": 1, "first": 2},
            middleware={str: lambda value, _context: value.lower()},
        )

    assert captured.value.serialized_key == "first"


def test_invalid_key_fails_before_value_serialization():
    class Value:
        pass

    calls = []

    def serialize_value(value, _context):
        calls.append(value)
        return "serialized"

    with pytest.raises(UnsupportedKeyTypeException):
        serialize(
            {1: Value()},
            middleware={Value: serialize_value},
        )

    assert calls == []
