from dataclasses import dataclass
from enum import Enum

import pytest

from src.pserialize import (
    TypeMismatchException,
    UnionDeserializationException,
    deserialize,
)
from src.pserialize.deserialize import BaseDeserializationException


SECRET = "super-secret-token"


def assert_redacted(error: Exception) -> None:
    assert SECRET not in str(error)
    assert SECRET not in repr(error)


def test_top_level_type_mismatch_redacts_raw_value():
    with pytest.raises(TypeMismatchException) as captured:
        deserialize(SECRET, int)

    assert_redacted(captured.value)
    assert str(captured.value) == "Expected int, got str"
    assert captured.value.value == SECRET
    assert captured.value.expected_type is int
    assert captured.value.actual_type is str


def test_nested_object_error_retains_path_without_raw_value():
    @dataclass
    class TokenPayload:
        api_token: int

    with pytest.raises(BaseDeserializationException) as captured:
        deserialize({"api_token": SECRET}, TokenPayload)

    assert_redacted(captured.value)
    assert "api_token" in str(captured.value)
    assert "Expected int, got str" in str(captured.value)


def test_list_error_retains_index_without_raw_value():
    with pytest.raises(BaseDeserializationException) as captured:
        deserialize([SECRET], list[int])

    assert_redacted(captured.value)
    assert "[0]" in str(captured.value)
    assert "Expected int, got str" in str(captured.value)


def test_dictionary_value_error_does_not_render_value():
    with pytest.raises(BaseDeserializationException) as captured:
        deserialize({"token": SECRET}, dict[str, int])

    assert_redacted(captured.value)
    assert "dict[str,int].value" in str(captured.value)
    assert "Expected int, got str" in str(captured.value)


def test_union_error_redacts_value_and_retains_branch_diagnostics():
    with pytest.raises(UnionDeserializationException) as captured:
        deserialize(SECRET, int | float)

    assert_redacted(captured.value)
    assert "No union branch matched" in str(captured.value)
    assert "int: Expected int, got str" in str(captured.value)
    assert "float: Expected float, got str" in str(captured.value)
    assert captured.value.value == SECRET
    assert len(captured.value.branch_errors) == 2


def test_enum_failure_does_not_render_invalid_member_value():
    class AccessLevel(Enum):
        USER = "user"

    with pytest.raises(BaseDeserializationException) as captured:
        deserialize(SECRET, AccessLevel)

    assert_redacted(captured.value)
    assert str(captured.value) == "Deserialization failed (ValueError)"
    assert captured.value.value == SECRET


def test_arbitrary_underlying_cause_text_is_not_rendered():
    error = BaseDeserializationException(
        ValueError(f"invalid credential: {SECRET}"),
        SECRET,
    )

    assert_redacted(error)
    assert str(error) == "Deserialization failed (ValueError)"
    assert error.value == SECRET
    assert SECRET in str(error.error)
