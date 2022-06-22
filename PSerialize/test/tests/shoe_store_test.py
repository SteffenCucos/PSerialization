
from ...src.serialize import serialize

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
                [ShoeBox(12, "Jordans", Condition.EXCELLENT), ShoeBox(12, "Jordans", Condition.BAD)]
            ]
        )
    ]

    serialized = serialize(store)
    assert serialized == [
        {
            "rows": [
                [{"size": 10, "name": "Jordans", "condition": "Excellent"}, {"size": 10, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 11, "name": "Jordans", "condition": "Excellent"}, {"size": 11, "name": "Jordans", "condition": "Excellent"}],
                [{"size": 12, "name": "Jordans", "condition": "Excellent"}, {"size": 12, "name": "Jordans", "condition": "Bad"}]
            ]
        }
    ]

    assert False


