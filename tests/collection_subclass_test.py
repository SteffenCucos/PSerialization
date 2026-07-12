from collections import OrderedDict, defaultdict, namedtuple
from collections.abc import Mapping, Sequence

import pytest

from src.pserialize import serialize
from src.pserialize.serialize import SerializeCycleException


def test_list_subclass_preserves_elements():
    class IDs(list):
        pass

    assert serialize(IDs([1, 2, 3])) == [1, 2, 3]


def test_dict_subclass_preserves_entries():
    class Attributes(dict):
        pass

    assert serialize(Attributes(name="Alice", active=True)) == {
        "name": "Alice",
        "active": True,
    }


def test_tuple_subclass_preserves_elements():
    Point = namedtuple("Point", ["x", "y"])

    assert serialize(Point(2, 3)) == [2, 3]


def test_set_subclass_preserves_elements():
    class Labels(set):
        pass

    assert set(serialize(Labels(["a", "b"]))) == {"a", "b"}


def test_frozenset_subclass_preserves_elements():
    class FrozenLabels(frozenset):
        pass

    assert set(serialize(FrozenLabels(["a", "b"]))) == {"a", "b"}


def test_ordered_dict_preserves_entries():
    value = OrderedDict([("first", 1), ("second", 2)])

    assert list(serialize(value).items()) == [("first", 1), ("second", 2)]


def test_defaultdict_preserves_entries_without_invoking_factory():
    factory_calls = []

    def factory():
        factory_calls.append(True)
        return "default"

    value = defaultdict(factory, {"existing": 1})

    assert serialize(value) == {"existing": 1}
    assert factory_calls == []


def test_custom_mapping_protocol_preserves_entries():
    class ReadOnlyMapping(Mapping):
        def __init__(self, values):
            self._values = values

        def __getitem__(self, key):
            return self._values[key]

        def __iter__(self):
            return iter(self._values)

        def __len__(self):
            return len(self._values)

    assert serialize(ReadOnlyMapping({"name": "Alice"})) == {"name": "Alice"}


def test_custom_sequence_protocol_preserves_elements():
    class Values(Sequence):
        def __init__(self, values):
            self._values = tuple(values)

        def __getitem__(self, index):
            return self._values[index]

        def __len__(self):
            return len(self._values)

    assert serialize(Values([1, 2, 3])) == [1, 2, 3]


def test_collection_subclasses_serialize_nested_objects_recursively():
    class IDs(list):
        pass

    class Record:
        def __init__(self, identifier):
            self.identifier = identifier

    assert serialize(IDs([Record(1), Record(2)])) == [
        {"identifier": 1},
        {"identifier": 2},
    ]


def test_exact_type_middleware_takes_precedence_over_collection_protocol():
    class IDs(list):
        pass

    def serialize_ids(value, middleware):
        return {"count": len(value)}

    assert serialize(IDs([1, 2, 3]), middleware={IDs: serialize_ids}) == {"count": 3}


def test_list_subclass_cycles_are_still_rejected():
    class RecursiveList(list):
        pass

    value = RecursiveList()
    value.append(value)

    with pytest.raises(SerializeCycleException, match="cyclic object graph"):
        serialize(value)


def test_dict_subclass_cycles_are_still_rejected():
    class RecursiveDict(dict):
        pass

    value = RecursiveDict()
    value["self"] = value

    with pytest.raises(SerializeCycleException, match="cyclic object graph"):
        serialize(value)
