from dataclasses import dataclass

import pytest

from src.pserialize import TypeMismatchException, deserialize
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializeDictKeyException,
    DeserializeDictValueException,
    DeserializeListException,
)

from .models.enum import Number


@dataclass
class klass3:
    e: Number


@dataclass
class klass2:
    d: list[klass3]


@dataclass
class klass1:
    a: int
    b: float
    c: klass2


def test_fail_deserialize_nested_class():
    data = {
        "a": 2,
        "b": 1.0,
        "c": {
            "d": [
                {"e": "one"},
                {"e": "1"},
            ]
        },
    }

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(data, klass1)

    assert (
        str(captured.value)
        == "klass1 -> c:klass2 -> d:list[klass3][1] -> e:Number -> '1' |'1' is not a valid Number|"
    )


@pytest.mark.parametrize("target_type", [int, float])
def test_fail_deserialize_primitives_reports_type_mismatch(target_type):
    with pytest.raises(DeserializeClassException) as captured:
        deserialize("Not a number", target_type)

    mismatch = captured.value.error
    assert isinstance(mismatch, TypeMismatchException)
    assert mismatch.expected_type is target_type
    assert mismatch.actual_type is str
    assert f"Expected {target_type.__name__}, got str" in str(captured.value)


def test_fail_deserialize_list_retains_item_context():
    data = [123, 456, "SevenEightNine"]

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(data, list[int])

    list_error = captured.value.error
    assert isinstance(list_error, DeserializeListException)
    assert list_error.index == 2
    assert isinstance(list_error.error, TypeMismatchException)
    assert list_error.error.expected_type is int
    assert list_error.error.actual_type is str


def test_fail_deserialize_dict_value_retains_value_context():
    data = {
        "Key1": 123,
        "Key2": 456,
        "Key3": "SevenEightNine",
    }

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(data, dict[str, int])

    value_error = captured.value.error
    assert isinstance(value_error, DeserializeDictValueException)
    assert value_error.key == "Key3"
    assert isinstance(value_error.error, TypeMismatchException)
    assert value_error.error.expected_type is int
    assert value_error.error.actual_type is str


def test_fail_deserialize_dict_value_complex():
    data = {
        "Key1": {
            "a": 2,
            "b": 1.0,
            "c": {
                "d": [
                    {"e": "one"},
                    {"e": "1"},
                ]
            },
        }
    }

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(data, dict[str, klass1])

    assert (
        str(captured.value)
        == "dict[str,klass1].value -> c:klass2 -> d:list[klass3][1] -> e:Number -> '1' |'1' is not a valid Number|"
    )


def test_fail_deserialize_dict_key_retains_key_context():
    data = {
        1: 123,
        2: 456,
        "Three": 789,
    }

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(data, dict[int, int])

    key_error = captured.value.error
    assert isinstance(key_error, DeserializeDictKeyException)
    assert isinstance(key_error.error, TypeMismatchException)
    assert key_error.error.expected_type is int
    assert key_error.error.actual_type is str
