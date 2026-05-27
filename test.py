"""
This module provides the Entry class, representing a titled entry with a body.
It follows defensive coding principles, providing robust validation and PEP8 compliance.
"""

class Entry:
    """
    A class to represent an entry with a title and a body.

    Attributes:
        title (str): The title of the entry.
        body (str): The body content of the entry.
    """

    def __init__(self, title: str, body: str) -> None:
        """
        Initializes the Entry with a title and a body.

        Args:
            title (str): The title of the entry.
            body (str): The body content of the entry.

        Raises:
            TypeError: If title or body is not a string.
            ValueError: If title or body is empty or consists only of whitespace.
        """
        # Validate types
        if not isinstance(title, str) or not isinstance(body, str):
            raise TypeError("Title and Body must be strings")

        # Validate content (non-empty and not just whitespace)
        if not title.strip() or not body.strip():
            raise ValueError("Title and Body cannot be empty")

        self._title = title
        self._body = body

    @property
    def title(self) -> str:
        """str: The title of the entry."""
        return self._title

    @property
    def body(self) -> str:
        """str: The body content of the entry."""
        return self._body

    def __str__(self) -> str:
        """
        Returns a string representation of the entry in 'Title - Body' format.

        Returns:
            str: The formatted string.
        """
        return f"{self._title} - {self._body}"

    def __repr__(self) -> str:
        """
        Returns a developer-friendly string representation of the entry.

        Returns:
            str: The representation string.
        """
        return f"Entry(title={self._title!r}, body={self._body!r})"


if __name__ == "__main__":
    # Example usage
    try:
        sample_entry = Entry("Defensive Coding", "Always validate your inputs.")
        print(f"Entry created successfully: {sample_entry}")
    except (TypeError, ValueError) as e:
        print(f"Failed to create entry: {e}")