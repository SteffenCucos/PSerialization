from enum import Enum

class Condition(Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    BAD = "Bad"
    AWFUL = "Awful"

class ShoeBox():
    def __init__(self, size: int, name: str, condition: Condition):
        self.size = size
        self.name = name
        self.condition = condition
    
    def __str__(self):
        return "{} {} in {} condition".format(self.size, self.name, self.condition)

class Shelf():
    def __init__(self, rows: list[list[ShoeBox]]):
        self.rows = rows

    def __str__(self):
        s = ""
        for row in self.rows:
            for shoe in row:
                s += str(shoe) + ","
            s += "\n"
        return s