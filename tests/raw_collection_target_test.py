from collections import OrderedDict
from dataclasses import dataclass
from typing import Union

import pytest

from src.pserialize import Deserializer, deserialize
from src.pserialize.deserialize import (
    DeserializeClassException,
    DeserializationContext,
    TypeMismatchException,
)


@pytest.mark.parametrize(
    ("value", "target", "expected"),
    [
        ([1, 2], list, [1, 2]),
        ({"a": 1}, dict, {"a": 1}),
        ([1, 2], tuple, (1, 2)),
        ([1, 2, 2], set, {1, 2}),
        ([1, 2, 2], frozenset, frozenset({1, 2})),
    ],
)
def test_raw_collection_targets(value, target, expected):
    result = deserialize(value, target)

    assert result == expected
    assert type(result) is target


def test_raw_collection_targets_create_new_outer_collections():
    source_list = [1, 2]
    source_dict = {"a": 1}

    result_list = deserialize(source_list, list)
    result_dict = deserialize(source_dict, dict)

    assert result_list == source_list
    assert result_list is not source_list
    assert result_dict == source_dict
    assert result_dict is not source_dict


def test_raw_collection_annotations_work_inside_objects():
    @dataclass
    class Payload:
        items: list
        pair: tuple
        tags: set
        frozen: frozenset
        lookup: dict

    result = deserialize(
        {
            "items": [1, "two"],
            "pair": [3, "four"],
            "tags": ["a", "b", "a"],
            "frozen": [5, 6],
            "lookup": {"seven": 7},
        },
        Payload,
    )

    assert result == Payload(
        items=[1, "two"],
        pair=(3, "four"),
        tags={"a", "b"},
        frozen=frozenset({5, 6}),
        lookup={"seven": 7},
    )


@pytest.mark.parametrize(
    ("value", "target"),
    [
        ({"not": "a list"}, list),
        ("not a tuple", tuple),
        ({"not": "a set sequence"}, set),
        (b"not a frozenset sequence", frozenset),
        (["not", "a", "mapping"], dict),
    ],
)
def test_raw_collection_targets_validate_input_shape(value, target):
    with pytest.raises(DeserializeClassException) as captured:
        deserialize(value, target)

    assert isinstance(captured.value.error, TypeMismatchException)
    assert captured.value.error.expected_type is target


def test_raw_dict_accepts_mapping_implementations():
    source = OrderedDict([("first", 1), ("second", 2)])

    result = deserialize(source, dict)

    assert result == {"first": 1, "second": 2}
    assert type(result) is dict


def test_raw_list_accepts_non_text_sequence_implementations():
    assert deserialize(range(3), list) == [0, 1, 2]


def test_raw_collection_target_works_as_a_union_branch():
    result = deserialize([1, 2], Union[tuple, dict])

    assert result == (1, 2)
    assert type(result) is tuple


def test_user_middleware_overrides_raw_collection_fallback():
    observed = {}

    def deserialize_list(value, context: DeserializationContext):
        observed["registered"] = context.get(list)
        return ["overridden", len(value)]

    result = deserialize(
        [1, 2, 3],
        list,
        middleware={list: deserialize_list},
    )

    assert result == ["overridden", 3]
    assert observed["registered"] is deserialize_list


def test_internal_raw_collection_fallbacks_are_hidden_from_public_context():
    @dataclass
    class Envelope:
        items: list

    def deserialize_envelope(value, context: DeserializationContext):
        assert list not in context
        assert context.get(list) is None
        return Envelope(context.deserialize(value["items"], list))

    result = deserialize(
        {"items": [1, 2]},
        Envelope,
        middleware={Envelope: deserialize_envelope},
    )

    assert result == Envelope([1, 2])


def test_deserializer_convenience_api_supports_raw_collection_targets():
    deserializer = Deserializer()

    assert deserializer.deserialize([1, 2], tuple) == (1, 2)
    assert deserializer.deserialize({"a": 1}, dict) == {"a": 1}


def test_raw_collection_targets_do_not_invent_element_types():
    result = deserialize(["1", 2.0, True], list, coerce=True)

    assert result == ["1", 2.0, True]
    assert [type(value) for value in result] == [str, float, bool]
