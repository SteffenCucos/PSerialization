from typing import Union
from dataclasses import dataclass

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
