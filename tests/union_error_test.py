from dataclasses import dataclass
from typing import Union

import pytest

from src.pserialize import deserialize
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializationMismatch,
    TypeMismatchException,
    UnionDeserializationException,
)


def test_union_does_not_swallow_unexpected_middleware_error():
    class Exploding:
        pass

    def broken(value, middleware):
        raise RuntimeError("middleware bug")

    with pytest.raises(RuntimeError, match="middleware bug"):
        deserialize(
            "5",
            Union[Exploding, int],
            middleware={Exploding: broken},
            coerce=True,
        )


def test_union_does_not_swallow_attribute_error_from_middleware():
    class Exploding:
        pass

    def broken(value, middleware):
        raise AttributeError("broken middleware")

    with pytest.raises(AttributeError, match="broken middleware"):
        deserialize(
            "5",
            Union[Exploding, int],
            middleware={Exploding: broken},
            coerce=True,
        )


def test_union_does_not_swallow_constructor_error():
    class Exploding:
        value: int

        def __init__(self, value: int):
            raise RuntimeError("constructor bug")

    with pytest.raises(RuntimeError, match="constructor bug"):
        deserialize(
            {"value": 1},
            Union[Exploding, dict[str, int]],
        )


def test_top_level_unexpected_middleware_error_is_not_wrapped():
    class Exploding:
        pass

    def broken(value, middleware):
        raise RuntimeError("top-level middleware bug")

    with pytest.raises(RuntimeError, match="top-level middleware bug"):
        deserialize("value", Exploding, middleware={Exploding: broken})


def test_expected_object_mismatch_allows_later_union_branch():
    @dataclass
    class First:
        first: int

    @dataclass
    class Second:
        second: int

    result = deserialize({"second": 2}, Union[First, Second])

    assert result == Second(2)


def test_middleware_can_explicitly_signal_branch_mismatch():
    class Custom:
        pass

    def not_this_branch(value, middleware):
        raise TypeMismatchException(value, Custom, type(value), "not a Custom value")

    result = deserialize(
        "5",
        Union[Custom, int],
        middleware={Custom: not_this_branch},
        coerce=True,
    )

    assert result == 5


def test_all_expected_union_failures_are_retained():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize("not-a-number", Union[int, float])

    union_error = captured.value.error
    assert isinstance(union_error, UnionDeserializationException)
    assert isinstance(union_error, DeserializationMismatch)
    assert union_error.allowed_types == (int, float)
    assert [branch_type for branch_type, _ in union_error.branch_errors] == [int, float]
    assert all(
        isinstance(error, TypeMismatchException)
        for _, error in union_error.branch_errors
    )
    assert "int:" in str(union_error)
    assert "float:" in str(union_error)


def test_nested_union_failure_retains_field_context():
    @dataclass
    class Payload:
        value: Union[int, float]

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"value": "invalid"}, Payload)

    field_error = captured.value.error
    assert isinstance(field_error, DeserializeClassException)
    assert field_error.field_name == "value"
    assert isinstance(field_error.error, UnionDeserializationException)


def test_non_mapping_object_input_is_an_expected_branch_mismatch():
    @dataclass
    class Payload:
        value: int

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(4.5, Union[Payload, int])

    union_error = captured.value.error
    assert isinstance(union_error, UnionDeserializationException)
    assert isinstance(union_error.branch_errors[0][1], TypeMismatchException)


def test_non_sequence_collection_input_is_an_expected_branch_mismatch():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"value": 1}, Union[list[int], tuple[int, ...]])

    union_error = captured.value.error
    assert isinstance(union_error, UnionDeserializationException)
    assert len(union_error.branch_errors) == 2
    assert all(
        isinstance(error, TypeMismatchException)
        for _, error in union_error.branch_errors
    )
