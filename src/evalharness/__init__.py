"""A record-first harness for LLM evals."""

__all__ = ["greeting"]


def greeting(name: str) -> str:
    """Return the greeting for `name`.

    Raises:
        ValueError: when `name` is empty.
    """
    if not name.strip():
        msg = "name must not be empty"
        raise ValueError(msg)
    return f"Hello, {name.strip()}!"
