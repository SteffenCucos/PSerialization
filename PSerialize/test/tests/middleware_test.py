
from datetime import datetime

from  ...src.serialize import Serializer
from  ...src.deserialize import Deserializer

def serialize_date(value: object):
    assert type(value) is datetime

    return repr(value)

def deserialize_date(value: object):
    assert type(value) is str

    arg_str = value.split("(")[1]
    arg_str = arg_str.replace(")", "")
    args = arg_str.strip(" ").split(",")
    args = [int(arg) for arg in args]

    return datetime(*args)

serializer = Serializer(middleware={datetime: serialize_date})
deserializer = Deserializer(middleware={datetime: deserialize_date})


def test_serialize_datetime():
    date = datetime(2022, 7, 25, 11, 3, 44, 21000)

    serialized = serializer.serialize(date)

    assert serialized == "datetime.datetime(2022, 7, 25, 11, 3, 44, 21000)"

def test_deserialize_datetime():
    date = "datetime.datetime(2022, 7, 25, 11, 3, 44, 21000)"

    deserialized = deserializer.deserialize(date, datetime)

    assert deserialized == datetime(2022, 7, 25, 11, 3, 44, 21000)