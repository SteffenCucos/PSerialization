# PSerialization

A Python library for serializing and deserializing Python objects into primitive data structures, then reconstructing typed Python objects from those primitives.

This is useful when moving Python objects through JSON-like systems, configuration files, or document databases where type information is not preserved automatically.

## Features

- Serialize simple Python objects into primitive structures.
- Deserialize primitive structures back into typed objects.
- Support parameterized and raw collection targets.
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

## Collection targets

Parameterized collections validate and deserialize their elements. Raw built-in
collection targets accept the corresponding serialized shape and preserve their
element values without inventing element types.

```python
from pserialize import deserialize

assert deserialize([1, 2], list) == [1, 2]
assert deserialize([1, 2], tuple) == (1, 2)
assert deserialize([1, 2], set) == {1, 2}
assert deserialize([1, 2], frozenset) == frozenset({1, 2})
assert deserialize({"one": 1}, dict) == {"one": 1}

# Parameterized targets apply their declared element types.
assert deserialize(["1", "2"], list[int], coerce=True) == [1, 2]
```

Sequence targets reject mappings and text-like inputs. Dictionary targets require
a mapping-shaped input. Raw collection targets create a new outer collection,
while untyped nested element values are preserved as supplied.

## Dictionary keys

Serialized mappings use JSON-compatible string keys. A source mapping key must
be a string, and serialization middleware applied to that key must also return a
string. Non-string keys raise `UnsupportedKeyTypeException` instead of failing
later with an unhashable-key error or producing output that JSON consumers handle
inconsistently.

```python
from pserialize import UnsupportedKeyTypeException, serialize

assert serialize({"one": 1}) == {"one": 1}

try:
    serialize({1: "one"})
except UnsupportedKeyTypeException:
    pass
```

If middleware transforms two distinct string keys into the same output key,
serialization raises `SerializedKeyCollisionException` rather than silently
overwriting an entry.

## Middleware example

Middleware always receives two arguments: the value and a context object. The
context is also a read-only view of the middleware registry. Use
`context.serialize(...)` or `context.deserialize(...)` for recursive work so
the active middleware and configuration are preserved.

```python
from datetime import datetime
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer
from pserialize import DeserializationContext, SerializationContext

def serialize_datetime(
    value: datetime,
    context: SerializationContext,
) -> str:
    return value.isoformat()

def deserialize_datetime(
    value: object,
    context: DeserializationContext,
) -> datetime:
    if not isinstance(value, str):
        raise TypeError("datetime input must be a string")
    return datetime.fromisoformat(value)

serializer = Serializer(middleware={datetime: serialize_datetime})
deserializer = Deserializer(middleware={datetime: deserialize_datetime})

date = datetime(2022, 7, 25, 11, 3, 44, 21000)
serialized = serializer.serialize(date)
deserialized = deserializer.deserialize(serialized, datetime)

assert serialized == "2022-07-25T11:03:44.021000"
assert deserialized == date
```

## Development notes

- Add tests for custom middleware behavior before changing serialization logic.
- Document supported Python versions once the package metadata is finalized.
- Keep examples in sync with the package API.

## License

No license has been selected yet.
