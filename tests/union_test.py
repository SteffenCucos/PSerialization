
from typing import Union
from dataclasses import dataclass

from src.pserialize import serialize, deserialize

def test_union():

    @dataclass
    class A:
        a: Union[float, int, str]

    a_list = [A(1), A("4"), A("four")]

    serialized = serialize(a_list)

    assert serialized == [
        {"a":1},
        {"a":"4"},
        {"a":"four"}
    ]

    deserialized = deserialize(serialized, list[A])
    # "4" can be coerced to int(4), and since int appears 
    # in the Union type first it takes precedent over str
    expected = [A(1), A(4.0), A("four")]

    assert a_list != expected
    assert deserialized == expected

