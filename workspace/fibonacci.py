#!/usr/bin/env python3
import sys
from typing import List, Generator


def fibonacci_sequence(n: int) -> Generator[int, None, None]:
    """
    Yields the first n numbers of the Fibonacci sequence.

    The sequence starts with 0, 1, 1, 2, 3, 5, ...

    Args:
        n (int): The number of Fibonacci numbers to generate.

    Yields:
        int: The next number in the Fibonacci sequence.

    Raises:
        TypeError: If n is not an integer.
        ValueError: If n is a negative integer.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be a non-negative integer, got {n}")

    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def get_fibonacci_list(n: int) -> List[int]:
    """
    Returns a list of the first n numbers of the Fibonacci sequence.

    Args:
        n (int): The number of Fibonacci numbers to generate.

    Returns:
        List[int]: A list containing the first n Fibonacci numbers.
    """
    return list(fibonacci_sequence(n))


def main() -> None:
    """
    Main entry point for the module. Provides a basic demonstration 
    and CLI interface.
    """
    if len(sys.argv) > 1:
        try:
            arg = sys.argv[1]
            n = int(arg)
            print(get_fibonacci_list(n))
        except ValueError:
            print(f"Error: Invalid input '{sys.argv[1]}'. Please provide a non-negative integer.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default demonstration
        demo_n = 10
        print(f"First {demo_n} Fibonacci numbers:")
        print(get_fibonacci_list(demo_n))


if __name__ == "__main__":
    main()