
from dataclasses import dataclass


@dataclass
class C:
    c: float

@dataclass
class B:
    b: str

@dataclass
class A(B, C):
    a: int
