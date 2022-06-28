# PSerialization
Python library for serializing & deserializing between dicts & python objects. 

Useful for sending python objects to a system that may only be expecting to handle primitive types, as well as reconstructing python objects from systems that lack type information. I personally use this for editing/loading configuration files stored as json, and for loading objects from nosql dbs like MongoDB.


## Examples

    from pserialize import (
	    serialize,
	    deserialize
    )
    
    class Shoe():
	    def __init__(self, size: int, condition: str, brand: str):
		    self.size = size
		    self.condition = condition
		    self.brand = brand
    
	if __name__ == "__main__":
		shoes = [Shoe(11, "Good", "Nike"), Shoe(12, "Bad", "Geox")]
		
		# Serialize a python object into primitives
		serialized = serialize(shoes)
		
		assert serialized == [
			{ "size": 11, "condition": "Good", "brand": "Nike" },
			{ "size": 12, "condition": "Bad", "brand": "Geox" }
		]
		
		# Build back the object representation just from primitives
		deserialized = deserialize(serialized, Shoe)
		
		assert deserialized == shoes


