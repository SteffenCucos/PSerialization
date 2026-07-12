import sys
from dataclasses import dataclass
from typing import Optional, Union

import pytest

from src.pserialize import deserialize


MultiBranchOptional = Union[int, str, None]


def test_optional_union_uses_later_non_none_branch():
    assert deserialize("hello", MultiBranchOptional) == "hello"


def test_optional_union_preserves_existing_runtime_type_regardless_of_order():
    target_type = Union[str, int, None]

    result = deserialize(4, target_type)

    assert result == 4
    assert type(result) is int


def test_optional_union_can_deserialize_object_after_earlier_branch_fails():
    @dataclass
    class Payload:
        value: int

    target_type = Union[int, Payload, None]

    result = deserialize({"value": "4"}, target_type)

    assert result == Payload(4)


def test_optional_union_accepts_none():
    assert deserialize(None, MultiBranchOptional) is None


def test_optional_union_works_for_nested_object_field():
    @dataclass
    class Payload:
        value: MultiBranchOptional

    assert deserialize({"value": "hello"}, Payload) == Payload("hello")
    assert deserialize({"value": 4}, Payload) == Payload(4)
    assert deserialize({"value": None}, Payload) == Payload(None)


def test_optional_union_works_inside_collection():
    result = deserialize([1, "two", None], list[MultiBranchOptional])

    assert result == [1, "two", None]
    assert [type(value) for value in result] == [int, str, type(None)]


def test_simple_optional_behavior_is_unchanged():
    assert deserialize("4", Optional[int]) == 4
    assert deserialize(None, Optional[int]) is None


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_pep_604_optional_union_uses_all_non_none_branches():
    target_type = eval("int | str | None")

    assert deserialize("hello", target_type) == "hello"
    assert deserialize(4, target_type) == 4
    assert deserialize(None, target_type) is None


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_pep_604_optional_union_can_reach_object_branch():
    @dataclass
    class Payload:
        value: int

    target_type = eval("int | Payload | None")

    assert deserialize({"value": "4"}, target_type) == Payload(4)
