import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional, TypeVar

import pytest

from src.pserialize import NullNotAllowedException, deserialize
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializeDictValueException,
    DeserializeListException,
)


ConstrainedValue = TypeVar("ConstrainedValue", int, str)
BoundInt = TypeVar("BoundInt", bound=int)
UnconstrainedValue = TypeVar("UnconstrainedValue")


@pytest.mark.parametrize(
    "target_type",
    [
        int,
        str,
        float,
        bool,
        list[int],
        dict[str, int],
    ],
)
def test_none_is_rejected_for_non_nullable_top_level_targets(target_type):
    with pytest.raises(DeserializeClassException) as captured:
        deserialize(None, target_type)

    assert isinstance(captured.value.error, NullNotAllowedException)
    assert captured.value.error.target_type == target_type
    assert "None is not allowed for" in str(captured.value)


def test_none_is_accepted_for_any():
    assert deserialize(None, Any) is None


def test_none_is_accepted_for_none_type():
    assert deserialize(None, type(None)) is None


def test_none_is_accepted_for_typing_optional():
    assert deserialize(None, Optional[int]) is None


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_none_is_accepted_for_pep_604_optional():
    assert deserialize(None, eval("int | None")) is None


def test_literal_none_is_accepted():
    assert deserialize(None, Literal[None]) is None


def test_none_is_rejected_for_literal_without_none():
    with pytest.raises(DeserializeClassException, match="Expected one of"):
        deserialize(None, Literal["enabled"])


def test_none_is_rejected_for_nested_non_nullable_field():
    @dataclass
    class Model:
        value: int

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"value": None}, Model)

    field_error = captured.value.error
    assert isinstance(field_error, DeserializeClassException)
    assert field_error.field_name == "value"
    assert isinstance(field_error.error, NullNotAllowedException)
    assert field_error.error.target_type is int


def test_none_is_accepted_for_nested_optional_field():
    @dataclass
    class Model:
        value: Optional[int]

    assert deserialize({"value": None}, Model) == Model(None)


def test_none_is_rejected_for_non_nullable_collection_item():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize([1, None], list[int])

    list_error = captured.value.error
    assert isinstance(list_error, DeserializeListException)
    assert list_error.index == 1
    assert isinstance(list_error.error, NullNotAllowedException)


def test_none_is_accepted_for_optional_collection_item():
    assert deserialize([1, None], list[Optional[int]]) == [1, None]


def test_none_is_rejected_for_non_nullable_dictionary_value():
    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"value": None}, dict[str, int])

    dict_error = captured.value.error
    assert isinstance(dict_error, DeserializeDictValueException)
    assert dict_error.key == "value"
    assert isinstance(dict_error.error, NullNotAllowedException)


def test_nullability_is_enforced_before_middleware_runs():
    calls = []

    def deserialize_datetime(value, middleware):
        calls.append(value)
        return datetime.fromisoformat(value)

    with pytest.raises(DeserializeClassException) as captured:
        deserialize(None, datetime, middleware={datetime: deserialize_datetime})

    assert isinstance(captured.value.error, NullNotAllowedException)
    assert calls == []


def test_none_is_rejected_for_constrained_type_var_without_none():
    @dataclass
    class Box:
        value: ConstrainedValue

    with pytest.raises(DeserializeClassException, match="None is not allowed"):
        deserialize({"value": None}, Box)


def test_none_is_rejected_for_non_nullable_bound_type_var():
    @dataclass
    class Box:
        value: BoundInt

    with pytest.raises(DeserializeClassException, match="None is not allowed"):
        deserialize({"value": None}, Box)


def test_none_is_accepted_for_unconstrained_type_var():
    @dataclass
    class Box:
        value: UnconstrainedValue

    assert deserialize({"value": None}, Box) == Box(None)
