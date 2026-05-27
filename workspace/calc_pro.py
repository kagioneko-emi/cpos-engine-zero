"""
Advanced Calculator Module

This module provides robust arithmetic operations with comprehensive
error handling and type validation.
"""

from typing import Union, Any


def _validate_numeric(value: Any, name: str) -> float:
    """
    Validates that a value is numeric (int or float).

    Args:
        value: The value to validate.
        name: The name of the parameter for error reporting.

    Returns:
        float: The validated numeric value.

    Raises:
        TypeError: If the value is not an int or float.
        ValueError: If the value is NaN or Infinity.
    """
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"Parameter '{name}' must be a numeric type (int or float), "
            f"not {type(value).__name__}"
        )

    # Check for NaN or Infinity
    # NaN != NaN is a standard way to check for NaN without math.isnan
    if value != value or value in (float('inf'), float('-inf')):
        raise ValueError(f"Parameter '{name}' must be a finite number")

    return float(value)


def add(a: Union[int, float], b: Union[int, float]) -> float:
    """
    Adds two numbers together.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        float: The sum of a and b.

    Raises:
        TypeError: If either input is non-numeric.
        ValueError: If either input is non-finite.
    """
    valid_a = _validate_numeric(a, "a")
    valid_b = _validate_numeric(b, "b")
    return valid_a + valid_b


def subtract(a: Union[int, float], b: Union[int, float]) -> float:
    """
    Subtracts the second number from the first.

    Args:
        a: The number to subtract from.
        b: The number to subtract.

    Returns:
        float: The difference of a and b.

    Raises:
        TypeError: If either input is non-numeric.
        ValueError: If either input is non-finite.
    """
    valid_a = _validate_numeric(a, "a")
    valid_b = _validate_numeric(b, "b")
    return valid_a - valid_b


if __name__ == "__main__":
    # Basic usage demonstration
    try:
        val_a, val_b = 10, 5
        print(f"Addition: {val_a} + {val_b} = {add(val_a, val_b)}")
        print(f"Subtraction: {val_a} - {val_b} = {subtract(val_a, val_b)}")

        # Error handling demonstration
        print("\nTesting Error Handling:")

        print("Testing non-numeric input (string): ", end="")
        try:
            add(10, "5")
        except TypeError as e:
            print(f"Caught: {e}")

        print("Testing non-finite input (NaN): ", end="")
        try:
            subtract(float('nan'), 5)
        except ValueError as e:
            print(f"Caught: {e}")

    except Exception as exc:
        print(f"An unexpected error occurred: {exc}")