

from dataclasses import dataclass
from threading import Thread
import time

from ...src.deserialize import get_gil_safe_empty_constructor

def run_task(task, arguments=()):
    Thread(target=task, args=arguments).start()

def bad_init(self):
    pass

test1Failed = False
test1Error = ""
def test_gil_calls_empty_constructor_from_other_thread():
    @dataclass
    class A:
        a: str
        b: int

    def create_a():
        try:
            A("one", 2)
        except Exception as e:
            global test1Failed, test1Error
            test1Failed = True
            test1Error = str(e)

    def bad_init(self):
        pass

    def unsafe():
        old = A.__init__
        A.__init__ = bad_init
        time.sleep(0.1)
        A.__init__ = old

    run_task(unsafe)
    time.sleep(0.05)
    run_task(create_a)

    global test1Failed, test1Error
    assert test1Failed == True
    # Tried to pass self, a, b to empty constructor
    assert test1Error == "bad_init() takes 1 positional argument but 3 were given"

test2passed = False
def test_gil_safe_constructor_calls_correct_constructor():
    @dataclass
    class B:
        a: str
        b: int

    def create_a():
        B("one", 2)
        global test2passed
        test2passed = True

    def unsafe():
        old = B.__init__
        B.__init__ = get_gil_safe_empty_constructor(old)
        time.sleep(0.1)
        B.__init__ = old

    run_task(unsafe)
    time.sleep(0.05)
    run_task(create_a)

    global test2passed
    assert test2passed == True