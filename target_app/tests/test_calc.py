import pytest
from src.calc import divide, add

def test_add():
    assert add(2, 3) == 5

def test_divide():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    # This test is expected to fail or raise an unhandled exception in the current buggy version
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
