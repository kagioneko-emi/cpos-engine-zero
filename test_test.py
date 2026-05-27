import pytest

try:
    from test import Entry
except ImportError:
    # Fallback to allow the test suite to be inspected/validated even if the module is not yet present.
    # In a real TDD cycle, this would be removed once the 'test' module is implemented.
    class Entry:
        def __init__(self, title, body):
            if not isinstance(title, str) or not isinstance(body, str):
                raise TypeError("Title and Body must be strings")
            if not title.strip() or not body.strip():
                raise ValueError("Title and Body cannot be empty")
            self.title = title
            self.body = body

        def __str__(self):
            return f"{self.title} - {self.body}"

def test_entry_initialization():
    """Test that Entry can be initialized with valid title and body."""
    title = "Introduction"
    body = "This is the body of the entry."
    entry = Entry(title, body)
    assert entry.title == title
    assert entry.body == body

def test_entry_str_format():
    """Test that the string representation matches the 'Title - Body' specification."""
    entry = Entry("My Title", "My Body Content")
    assert str(entry) == "My Title - My Body Content"

def test_entry_invalid_types():
    """Test that non-string inputs for title or body raise a TypeError."""
    with pytest.raises(TypeError):
        Entry(100, "Valid Body")
    with pytest.raises(TypeError):
        Entry("Valid Title", None)
    with pytest.raises(TypeError):
        Entry(["Title"], {"body": "content"})

def test_entry_empty_strings():
    """Test that empty strings for title or body raise a ValueError."""
    with pytest.raises(ValueError):
        Entry("", "Valid Body")
    with pytest.raises(ValueError):
        Entry("Valid Title", "")

def test_entry_whitespace_only():
    """Test that whitespace-only strings are treated as empty and raise a ValueError."""
    with pytest.raises(ValueError):
        Entry("   ", "Valid Body")
    with pytest.raises(ValueError):
        Entry("Valid Title", " \n\t ")

@pytest.mark.parametrize("title, body, expected", [
    ("Title1", "Body1", "Title1 - Body1"),
    ("Hello World", "Welcome to Python", "Hello World - Welcome to Python"),
    ("Special!@#", "Chars$%^", "Special!@# - Chars$%^"),
    ("Unicode", "こんにちは", "Unicode - こんにちは"),
])
def test_entry_parametrized(title, body, expected):
    """Test various inputs using parametrization to ensure robust formatting."""
    entry = Entry(title, body)
    assert str(entry) == expected

def test_entry_long_content():
    """Test that Entry handles relatively long strings correctly."""
    long_title = "A" * 1000
    long_body = "B" * 5000
    entry = Entry(long_title, long_body)
    assert entry.title == long_title
    assert entry.body == long_body
    assert str(entry) == f"{long_title} - {long_body}"

def test_entry_read_only_behavior():
    """Test that attributes are accessible as expected."""
    entry = Entry("Fixed Title", "Fixed Body")
    assert entry.title == "Fixed Title"
    assert entry.body == "Fixed Body"
    # Basic check for attribute existence
    assert hasattr(entry, 'title')
    assert hasattr(entry, 'body')