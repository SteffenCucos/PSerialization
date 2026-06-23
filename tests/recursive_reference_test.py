from dataclasses import dataclass

from src.pserialize import serialize


@dataclass
class Node:
    name: str
    child: object = None


def test_self_referencing_list_raises_error():
    value = []
    value.append(value)

    error = None
    try:
        serialize(value)
    except Exception as e:
        error = e

    assert error is not None


def test_self_referencing_dict_raises_error():
    value = {}
    value["self"] = value

    error = None
    try:
        serialize(value)
    except Exception as e:
        error = e

    assert error is not None


def test_mutually_referencing_objects_raise_error():
    parent = Node("parent")
    child = Node("child")
    parent.child = child
    child.child = parent

    error = None
    try:
        serialize(parent)
    except Exception as e:
        error = e

    assert error is not None


def test_shared_reference_without_recursion_is_allowed():
    child = Node("child")
    value = [child, child]

    assert serialize(value) == [
        {"name": "child", "child": None},
        {"name": "child", "child": None},
    ]
