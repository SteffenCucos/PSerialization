
from datetime import datetime

from src.pserialize.serialize import Serializer
from src.pserialize.deserialize import Deserializer
from src.pserialize.middleware.datetime import _datetime

serializer = Serializer(middleware={datetime: _datetime.serializer})
deserializer = Deserializer(middleware={datetime: _datetime.deserializer})


def test_serialize_datetime():
    date = datetime(2022, 7, 25, 11, 3, 44, 21000)

    serialized = serializer.serialize(date)

    assert serialized == "2022-07-25T11:03:44.021000"

def test_deserialize_datetime():
    date = "2022-07-25T11:03:44.021000"

    deserialized = deserializer.deserialize(date, datetime)

    assert deserialized == datetime(2022, 7, 25, 11, 3, 44, 21000)