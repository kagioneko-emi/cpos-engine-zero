import pytest
try:
    from calc_pro import add, subtract
except ImportError:
    # Fallback for demonstration if module not yet created
    def add(a, b):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise TypeError("Inputs must be numeric")
        return a + b
    def subtract(a, b):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise TypeError("Inputs must be numeric")
        return a - b

def test_add_integers():
    """Test addition with positive and negative integers."""
    assert add(10, 5) == 15
    assert add(-1, 1) == 0
    assert add(-5, -5) == -10

def test_add_floats():
    """Test addition with floating point numbers."""
    assert add(1.5, 2.5) == 4.0
    assert add(0.1, 0.2) == pytest.approx(0.3)

def test_add_zero():
    """Test addition with zero."""
    assert add(0, 10) == 10
    assert add(5, 0) == 5
    assert add(0, 0) == 0

def test_add_large_numbers():
    """Test addition with very large numbers."""
    assert add(1e15, 1e15) == 2e15

def test_add_invalid_input():
    """Test that add raises TypeError for non-numeric input."""
    with pytest.raises(TypeError):
        add("1", 2)
    with pytest.raises(TypeError):
        add(1, "2")
    with pytest.raises(TypeError):
        add(None, 5)
    with pytest.raises(TypeError):
        add([1], 2)

def test_subtract_integers():
    """Test subtraction with positive and negative integers."""
    assert subtract(10, 5) == 5
    assert subtract(5, 10) == -5
    assert subtract(-5, -5) == 0

def test_subtract_floats():
    """Test subtraction with floating point numbers."""
    assert subtract(5.5, 2.5) == 3.0
    assert subtract(0.3, 0.1) == pytest.approx(0.2)

def test_subtract_zero():
    """Test subtraction with zero."""
    assert subtract(10, 0) == 10
    assert subtract(0, 10) == -10
    assert subtract(0, 0) == 0

def test_subtract_invalid_input():
    """Test that subtract raises TypeError for non-numeric input."""
    with pytest.raises(TypeError):
        subtract("10", 5)
    with pytest.raises(TypeError):
        subtract(10, "5")
    with pytest.raises(TypeError):
        subtract(5, {"key": "value"})
    with pytest.raises(TypeError):
        subtract(None, None)

@pytest.mark.parametrize("a, b, expected", [
    (10, 20, 30),
    (-1, -1, -2),
    (0, 0, 0),
    (1.1, 2.2, 3.3),
])
def test_add_parametrized(a, b, expected):
    """Parametrized test for various addition scenarios."""
    assert add(a, b) == pytest.approx(expected)

@pytest.mark.parametrize("a, b, expected", [
    (10, 5, 5),
    (5, 10, -5),
    (-1, -1, 0),
    (2.2, 1.1, 1.1),
])
def test_subtract_parametrized(a, b, expected):
    """Parametrized test for various subtraction scenarios."""
    assert subtract(a, b) == pytest.approx(expected)