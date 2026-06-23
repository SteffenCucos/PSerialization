# PSerialization

A Python library for serializing and deserializing Python objects into primitive data structures, then reconstructing typed Python objects from those primitives.

This is useful when moving Python objects through JSON-like systems, configuration files, or document databases where type information is not preserved automatically.

## Features

- Serialize simple Python objects into primitive structures.
- Deserialize primitive structures back into typed objects.
- Support lists and nested object graphs.
- Allow custom middleware for special types such as `datetime.datetime`.

## Installation

For local development:

```bash
pip install -e .
```

For package publishing/build work:

```bash
python3 -m build
python3 -m twine upload --repository pypi dist/*
```

## Basic object example

```python
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer

serializer = Serializer()
deserializer = Deserializer()

class Shoe:
    def __init__(self, size: int, condition: str, brand: str):
        self.size = size
        self.condition = condition
        self.brand = brand

shoes = [Shoe(11, "Good", "Nike"), Shoe(12, "Bad", "Geox")]

serialized = serializer.serialize(shoes)
assert serialized == [
    {"size": 11, "condition": "Good", "brand": "Nike"},
    {"size": 12, "condition": "Bad", "brand": "Geox"},
]

deserialized = deserializer.deserialize(serialized, list[Shoe])
```

## Middleware example

```python
from datetime import datetime
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer

def serialize_datetime(value: datetime):
    return repr(value)

def deserialize_datetime(value: object):
    assert isinstance(value, str)
    arg_str = value.split("(")[1].replace(")", "")
    args = [int(arg) for arg in arg_str.strip(" ").split(",")]
    return datetime(*args)

serializer = Serializer(middleware={datetime: serialize_datetime})
deserializer = Deserializer(middleware={datetime: deserialize_datetime})

date = datetime(2022, 7, 25, 11, 3, 44, 21000)
serialized = serializer.serialize(date)
deserialized = deserializer.deserialize(serialized, datetime)

assert deserialized == date
```

## Development notes

- Add tests for custom middleware behavior before changing serialization logic.
- Document supported Python versions once the package metadata is finalized.
- Keep examples in sync with the package API.

## License

No license has been selected yet.
