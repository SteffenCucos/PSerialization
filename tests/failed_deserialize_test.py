from typing import Union
from src.pserialize import serialize, deserialize

from dataclasses import dataclass

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


# def test_fail_deserialize_class():
#     data = {
#         "a": 2,
#         "b": 1.0,
#         "c": {
#             "d": [{
#                 "e": "one"
#             },
#             {
#                 "e": "1"
#             }]
#         }
#     }

#     # data = {
#     #     "d": [{
#     #         "e": "stuff"
#     #     }]
#     # }

#     try:
#         value = deserialize({"one": "two"}, dict[str, float])
#         raise Exception(value)
#     except Exception as e:
#         s = str(e)

#         raise Exception(s)
#         #assert str(e) == "klass1 -> c:klass2 -> d:list[klass3][0] -> e:int = 'stuff' |invalid literal for int() with base 10: 'stuff'|"
#         #"klass1 -> c:klass2 -> d:list -> list[klass3][0] -> e:int = 'stuff' |invalid literal for int() with base 10: 'stuff'|"
#         #raise e
    