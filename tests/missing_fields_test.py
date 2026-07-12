from dataclasses import dataclass, field
from typing import Optional

import pytest

from src.pserialize import MissingRequiredFieldException, deserialize
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializeListException,
)


def test_missing_required_ordinary_constructor_parameter_is_rejected():
    class Model:
        def __init__(self, value: int):
            self.value = value

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({}, Model)

    assert isinstance(captured.value.error, MissingRequiredFieldException)
    assert captured.value.error.field_name == "value"
    assert captured.value.error.class_type is Model
    assert "Missing required field 'value' for Model" in str(captured.value)


def test_constructor_is_not_called_when_required_field_is_missing():
    calls = []

    class Model:
        def __init__(self, value: int):
            calls.append(value)
            self.value = value

    with pytest.raises(DeserializeClassException):
        deserialize({}, Model)

    assert calls == []


def test_optional_annotation_without_default_is_still_required():
    @dataclass
    class Model:
        value: Optional[int]

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({}, Model)

    assert isinstance(captured.value.error, MissingRequiredFieldException)
    assert captured.value.error.field_name == "value"


def test_optional_annotation_with_default_none_may_be_omitted():
    @dataclass
    class Model:
        value: Optional[int] = None

    assert deserialize({}, Model) == Model(None)


def test_explicit_none_is_distinct_from_missing_optional_field():
    @dataclass
    class Model:
        value: Optional[int]

    assert deserialize({"value": None}, Model) == Model(None)


def test_dataclass_scalar_default_is_applied_by_constructor():
    @dataclass
    class Model:
        value: int
        label: str = "default"

    assert deserialize({"value": 1}, Model) == Model(1, "default")


def test_dataclass_default_factory_is_applied_by_constructor():
    @dataclass
    class Model:
        value: int
        tags: list[str] = field(default_factory=list)

    first = deserialize({"value": 1}, Model)
    second = deserialize({"value": 2}, Model)

    assert first == Model(1, [])
    assert second == Model(2, [])
    assert first.tags is not second.tags


def test_supplied_value_replaces_dataclass_default_factory():
    @dataclass
    class Model:
        value: int
        tags: list[str] = field(default_factory=list)

    assert deserialize({"value": 1, "tags": ["a"]}, Model) == Model(1, ["a"])


def test_required_keyword_only_parameter_is_rejected():
    class Model:
        def __init__(self, *, value: int):
            self.value = value

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({}, Model)

    assert isinstance(captured.value.error, MissingRequiredFieldException)
    assert captured.value.error.field_name == "value"


def test_keyword_only_default_is_preserved():
    class Model:
        def __init__(self, *, value: int = 4):
            self.value = value

        def __eq__(self, other):
            return isinstance(other, Model) and self.value == other.value

    assert deserialize({}, Model) == Model(value=4)


def test_nested_missing_field_retains_parent_field_context():
    @dataclass
    class Child:
        required: int

    @dataclass
    class Parent:
        child: Child

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({"child": {}}, Parent)

    parent_field_error = captured.value.error
    assert isinstance(parent_field_error, DeserializeClassException)
    assert parent_field_error.field_name == "child"
    assert isinstance(parent_field_error.error, MissingRequiredFieldException)
    assert parent_field_error.error.field_name == "required"


def test_missing_field_in_collection_retains_item_index():
    @dataclass
    class Model:
        required: int

    with pytest.raises(DeserializeClassException) as captured:
        deserialize([{}], list[Model])

    list_error = captured.value.error
    assert isinstance(list_error, DeserializeListException)
    assert list_error.index == 0
    assert isinstance(list_error.error, MissingRequiredFieldException)
    assert list_error.error.field_name == "required"


def test_multiple_missing_fields_report_first_constructor_parameter():
    @dataclass
    class Model:
        first: int
        second: str

    with pytest.raises(DeserializeClassException) as captured:
        deserialize({}, Model)

    assert isinstance(captured.value.error, MissingRequiredFieldException)
    assert captured.value.error.field_name == "first"
