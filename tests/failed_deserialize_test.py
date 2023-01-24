from dataclasses import dataclass
from typing import Union

from src.pserialize import deserialize, serialize

from .models.enum import Number


@dataclass
class klass3:
    e: Number


@dataclass
class klass2:
    d: list[klass3]


@dataclass
class klass1:
    a: int
    b: float
    c: klass2


def test_fail_deserialize_nested_class():
    data = {
        "a": 2,
        "b": 1.0,
        "c": {
            "d": [{
                "e": "one"
            },
            {
                "e": "1"
            }]
        }
    }

    try:
        deserialize(data, klass1)
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "klass1 -> c:klass2 -> d:list[klass3][1] -> e:Number -> '1' |'1' is not a valid Number|"
    
def test_fail_deserialize_primitives_int():
    data = "Not a number"

    try:
        deserialize(data, int)
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "int -> 'Not a number' |invalid literal for int() with base 10: 'Not a number'|"

def test_fail_deserialize_primitives_float():
    data = "Not a number"

    try:
        deserialize(data, float)
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "float -> 'Not a number' |could not convert string to float: 'Not a number'|"


def test_fail_deserialize_list():
    data = [123, 456, "SevenEightNine"]

    try:
        deserialize(data, list[int])
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "list[int][2] -> 'SevenEightNine' |invalid literal for int() with base 10: 'SevenEightNine'|"

def test_fail_deserialize_dict_value():
    data = {
        "Key1": 123,
        "Key2": 456,
        "Key3": "SevenEightNine"
    }

    try:
        deserialize(data, dict[str, int])
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "dict[str,int].value -> 'SevenEightNine' |invalid literal for int() with base 10: 'SevenEightNine'|"

def test_fail_deserialize_dict_value_complex():
    data = {
        "Key1": {
            "a": 2,
            "b": 1.0,
            "c": {
                "d": [{
                    "e": "one"
                },
                {
                    "e": "1"
                }]
            }
        }
    }

    try:
        deserialize(data, dict[str, klass1])
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "dict[str,klass1].value -> c:klass2 -> d:list[klass3][1] -> e:Number -> '1' |'1' is not a valid Number|"

        
def test_fail_deserialize_dict_key():
    data = {
        1: 123,
        2: 456,
        "Three": 789
    }

    try:
        deserialize(data, dict[int, int])
    except Exception as e:
        error = e

    assert error is not None
    assert str(error) == "dict[int,int].key -> 'Three' |invalid literal for int() with base 10: 'Three'|"
