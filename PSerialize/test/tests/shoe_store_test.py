
from  ...src.serialize import default_serializer as serializer
from  ...src.deserialize import default_deserializer as deserializer

from ..models.shoe_store import (
    Shelf,
    ShoeBox,
    Condition
)


def test_serialize_store():
    store = [
        Shelf(
            rows=[
                [ShoeBox(10, "Jordans", Condition.EXCELLENT), ShoeBox(10, "Jordans", Condition.EXCELLENT)],
                [ShoeBox(11, "Jordans", Condition.EXCELLENT), ShoeBox(11, "Jordans", Condition.EXCELLENT)],
                [ShoeBox(12, "Jordans", Condition.EXCELLENT), ShoeBox(12,None, Condition.BAD)]
            ]
        )
    ]

    serialized = serializer.serialize(store)
    assert serialized == [
        {
            "rows": [
                [{"size": 10, "name": "Jordans", "condition": "Excellent"}, {"size": 10, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 11, "name": "Jordans", "condition": "Excellent"}, {"size": 11, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 12, "name": "Jordans", "condition": "Excellent"}, {"size": 12, "name": None, "condition": "Bad"}]
            ]
        }
    ]

def test_deserialize_store():
    expected = [
        Shelf(
            rows=[
                [ShoeBox(10, "Jordans", Condition.EXCELLENT), ShoeBox(10, "Jordans", Condition.EXCELLENT)],
                [ShoeBox(11, "Jordans", Condition.EXCELLENT), ShoeBox(11, "Jordans", Condition.EXCELLENT)],
                [ShoeBox(12, "Jordans", Condition.EXCELLENT), ShoeBox(12, "Jordans", Condition.BAD)]
            ]
        )
    ]

    json = [
        {
            "rows": [
                [{"size": 10, "name": "Jordans", "condition": "Excellent"}, {"size": 10, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 11, "name": "Jordans", "condition": "Excellent"}, {"size": 11, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 12, "name": "Jordans", "condition": "Excellent"}, {"size": 12, "name": "Jordans", "condition": "Bad"}]
            ]
        }
    ]

    deserialized = deserializer.deserialize(json, list[Shelf])

    assert deserialized == expected



