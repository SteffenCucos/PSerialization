from src.pserialize import serialize, deserialize

from .models.dataclass import (
    A
)

def test_serialize_dataclass():
    a = A(3.0, "bee", 1)

    expected = {
        "c": 3.0,
        "b": "bee",
        "a": 1
    }

    assert serialize(a) == expected

def test_deserialize_dataclass():
    dct = {
        "c": 3.0,
        "b": "bee",
        "a": 1
    }
    
    assert deserialize(dct, A) == A(3.0, "bee", 1)