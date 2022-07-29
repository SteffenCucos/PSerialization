# PSerialization
Python library for serializing & deserializing python objects.

Out of the box support for "basic" object de/serialization, that is objects that hold all of their state in __ dict __ and have a trivial __ new __.

For more complicated types like datetime.datetime, users of this library can supply custom middleware to handle de/serializing those types.

Useful for sending python objects to a system that may only be expecting to handle primitive types, as well as reconstructing python objects from systems that lack type information. I personally use this for editing/loading configuration files stored as json, and for loading objects from nosql dbs like MongoDB.


## 'Basic' Object Example
```python
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer

serializer = Serializer()
deserializer = Deserializer()

class Shoe():
	def __init__(self, size: int, condition: str, brand: str):
		self.size = size
		self.condition = condition
		self.brand = brand

if __name__ == "__main__":
	shoes = [Shoe(11, "Good", "Nike"), Shoe(12, "Bad", "Geox")]
	
	# Serialize a python object into primitives
	serialized = serializer.serialize(shoes)
	
	assert serialized == [
		{ "size": 11, "condition": "Good", "brand": "Nike" },
		{ "size": 12, "condition": "Bad", "brand": "Geox" }
	]
	
	# Build back the object representation just from primitives
	deserialized = deserializer.deserialize(serialized, Shoe)
	
	assert deserialized == shoes
```


## Middleware Example
```python
from datetime import datetime
from pserialize.serializer import Serializer
from pserialize.deserializer import Deserializer

def serialize_datetime(date: datetime):
	return repr(date)

def deserialize_date(value: object):
	assert type(value) is str

	arg_str = value.split("(")[1]
	arg_str = arg_str.replace(")", "")
	args = arg_str.strip(" ").split(",")
	args = [int(arg) for arg in args]

	return datetime(*args)

serializer = Serializer(middleware={datetime: serialize_datetime})
deserializer = Deserializer(middleware={datetime: deserialize_datetime})

if __name__ == "__main__":
	date = datetime(2022, 7, 25, 11, 3, 44, 21000)

	# Serialized using the custom function
	serialized = serializer.serialize(date)
	assert serialized == "datetime.datetime(2022, 7, 25, 11, 3, 44, 21000)"

	# Deserialized back into the correct type
	deserialized = deserializer.deserialize(serialized, datetime)
	assert deserialized == date

```
