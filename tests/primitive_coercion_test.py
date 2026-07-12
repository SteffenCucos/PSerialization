from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Union

import pytest

from src.pserialize import (
    Deserializer,
    TypeMismatchException,
    deserialize,
)
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializeDictValueException,
    DeserializeListException,
)


ConstrainedScalar = TypeVar("ConstrainedScalar", int, str)


def assert_type_mismatch(value, target_type, *, coerce=False):
    with pytest.raises(DeserializeClassException) as captured:
        deserialize(value, target_type, coerce=coerce)

    assert isinstance(captured.value.error, TypeMismatchException)
    assert captured.value.error.expected_type is target_type
    assert captured.value.error.actual_type is type(value)
    return captured.value.error


@pytest.mark.parametrize(
    ("value", "target_type"),
    [
        ("4", int),
        (4.0, int),
        (True, int),
        (4, float),
        (0, str),
        ("false", bool),
    ],
)
def test_primitive_validation_is_strict_by_default(value, target_type):
    assert_type_mismatch(value, target_type)


@pytest.mark.parametrize(
    ("value", "target_type"),
    [
        (4, int),
        (4.0, float),
        ("four", str),
        (False, bool),
    ],
)
def test_exact_primitive_types_are_returned_unchanged(value, target_type):
    result = deserialize(value, target_type)

    assert result is value


@pytest.mark.parametrize("value", ["true", "1", "yes", "on", " TRUE "])
def test_boolean_true_strings_require_explicit_coercion(value):
    assert deserialize(value, bool, coerce=True) is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", " FALSE "])
def test_boolean_false_strings_require_explicit_coercion(value):
    assert deserialize(value, bool, coerce=True) is False


@pytest.mark.parametrize(("value", "expected"), [(1, True), (0, False)])
def test_boolean_integer_coercion_is_limited_to_zero_and_one(value, expected):
    assert deserialize(value, bool, coerce=True) is expected


@pytest.mark.parametrize("value", ["truthy", 2, -1, 0.0, [], None])
def test_invalid_boolean_coercions_are_rejected(value):
    if value is None:
        with pytest.raises(DeserializeClassException):
            deserialize(value, bool, coerce=True)
    else:
        assert_type_mismatch(value, bool, coerce=True)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("42", 42),
        (" -42 ", -42),
        ("+7", 7),
        (4.0, 4),
    ],
)
def test_safe_integer_coercions(value, expected):
    assert deserialize(value, int, coerce=True) == expected


@pytest.mark.parametrize("value", [4.9, True, "4.0", "1_000", float("inf")])
def test_lossy_or_ambiguous_integer_coercions_are_rejected(value):
    assert_type_mismatch(value, int, coerce=True)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("4.5", 4.5),
        ("1e3", 1000.0),
        (4, 4.0),
    ],
)
def test_safe_float_coercions(value, expected):
    result = deserialize(value, float, coerce=True)

    assert result == expected
    assert type(result) is float


@pytest.mark.parametrize(
    "value",
    [
        "nan",
        "inf",
        "-inf",
        9007199254740993,
        True,
    ],
)
def test_non_finite_or_inexact_float_coercions_are_rejected(value):
    assert_type_mismatch(value, float, coerce=True)


def test_values_are_never_implicitly_stringified():
    assert_type_mismatch(0, str)
    assert_type_mismatch(0, str, coerce=True)


def test_coercion_policy_propagates_through_nested_objects():
    @dataclass
    class Model:
        count: int
        enabled: bool

    result = deserialize(
        {"count": "4", "enabled": "false"},
        Model,
        coerce=True,
    )

    assert result == Model(4, False)


def test_nested_primitive_mismatch_retains_field_context():
    @dataclass
    class Model:
        count: int

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"count": "4"}, Model)

    field_error = captured.value.error
    assert isinstance(field_error, DeserializeClassException)
    assert field_error.field_name == "count"
    assert isinstance(field_error.error, TypeMismatchException)


def test_coercion_policy_propagates_through_collections_and_mappings():
    assert deserialize(["1", 2.0], list[int], coerce=True) == [1, 2]
    assert deserialize(
        {"first": "1", "second": 2.0},
        dict[str, int],
        coerce=True,
    ) == {"first": 1, "second": 2}


def test_collection_mismatch_retains_index_context():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize([1, "2"], list[int])

    list_error = captured.value.error
    assert isinstance(list_error, DeserializeListException)
    assert list_error.index == 1
    assert isinstance(list_error.error, TypeMismatchException)


def test_mapping_mismatch_retains_value_context():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"value": "2"}, dict[str, int])

    mapping_error = captured.value.error
    assert isinstance(mapping_error, DeserializeDictValueException)
    assert mapping_error.key == "value"
    assert isinstance(mapping_error.error, TypeMismatchException)


def test_coercion_policy_propagates_through_unions():
    target_type = Union[int, str]

    with pytest.raises(DeserializeClassException):
        deserialize(4.0, target_type)

    assert deserialize(4.0, target_type, coerce=True) == 4


def test_coercion_policy_propagates_through_constrained_typevars():
    @dataclass
    class Box:
        value: ConstrainedScalar

    with pytest.raises(DeserializeClassException):
        deserialize({"value": 4.0}, Box)

    assert deserialize({"value": 4.0}, Box, coerce=True) == Box(4)


def test_deserializer_convenience_api_exposes_coercion_policy():
    deserializer = Deserializer()

    assert deserializer.deserialize("42", int, coerce=True) == 42


def test_primitive_subclasses_require_explicit_coercion():
    class UserId(int):
        pass

    assert_type_mismatch("42", UserId)

    result = deserialize("42", UserId, coerce=True)

    assert result == 42
    assert type(result) is UserId


def test_string_backed_enums_are_not_treated_as_primitives():
    class Status(str, Enum):
        ACTIVE = "active"

    assert deserialize("active", Status) is Status.ACTIVE


def test_coerce_must_be_boolean():
    with pytest.raises(TypeError, match="coerce must be a bool"):
        deserialize("42", int, coerce="yes")
