from src.pserialize.serialize import default_serializer as serializer
from src.pserialize.deserialize import default_deserializer as deserializer

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

    assert serializer.serialize(a) == expected

def test_deserialize_dataclass():
    dct = {
        "c": 3.0,
        "b": "bee",
        "a": 1
    }
    
    assert deserializer.deserialize(dct, A) == A(3.0, "bee", 1)