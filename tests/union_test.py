import sys
from typing import Union
from dataclasses import dataclass

import pytest

from src.pserialize import serialize, deserialize


def test_union_prefers_existing_value_type_before_coercion():

    @dataclass
    class A:
        a: Union[float, int, str]

    a_list = [A(1), A("4"), A("four")]

    serialized = serialize(a_list)

    assert serialized == [
        {"a": 1},
        {"a": "4"},
        {"a": "four"}
    ]

    deserialized = deserialize(serialized, list[A])

    assert deserialized == a_list


def test_union_still_coerces_when_value_is_not_already_allowed_type():

    @dataclass
    class A:
        a: Union[int, str]

    deserialized = deserialize({"a": 4.0}, A)

    assert deserialized == A(4)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_pep_604_union_prefers_existing_value_type_before_coercion():

    @dataclass
    class A:
        a: eval("float | int | str")

    a_list = [A(1), A("4"), A("four")]

    serialized = serialize(a_list)
    deserialized = deserialize(serialized, list[A])

    assert deserialized == a_list


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_pep_604_union_still_coerces_when_value_is_not_already_allowed_type():

    @dataclass
    class A:
        a: eval("int | str")

    deserialized = deserialize({"a": 4.0}, A)

    assert deserialized == A(4)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP 604 unions require Python 3.10+")
def test_pep_604_optional_accepts_none_and_deserializes_real_type():

    @dataclass
    class A:
        a: eval("int | None")

    assert deserialize({"a": None}, A) == A(None)
    assert deserialize({"a": "4"}, A) == A(4)
