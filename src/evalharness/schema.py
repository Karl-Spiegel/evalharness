"""A minimal JSON Schema validator for the contract schemas in `docs/contract/`.

It covers only the keywords the two contract schemas use. It raises on any other keyword, so a
schema that outgrows it fails loud instead of passing unchecked.
"""

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path

# The contract lives in the repository, not in the package; this path holds for a source checkout.
CONTRACT = Path(__file__).parent.parent.parent / "docs" / "contract"
RECORD_SCHEMA = CONTRACT / "record.schema.json"

type Json = bool | int | float | str | Sequence[Json] | Mapping[str, Json] | None
type Schema = Mapping[str, Json]

ANNOTATIONS = frozenset({"$schema", "$id", "title", "description"})
KEYWORDS = frozenset(
    {
        "type",
        "const",
        "enum",
        "required",
        "properties",
        "additionalProperties",
        "minProperties",
        "items",
        "minimum",
        "maximum",
        "minLength",
        "pattern",
        "format",
        "if",
        "then",
        "else",
        "allOf",
    }
)


def _type_of(value: Json) -> str:
    """Return the JSON Schema type name of a decoded JSON value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    return "number" if isinstance(value, float) else "array"


def _has_type(value: Json, name: str) -> bool:
    """Return whether value has the JSON Schema type name; an integer is also a number."""
    actual = _type_of(value)
    return actual == name or (name == "number" and actual == "integer")


def _format_ok(value: str, fmt: str) -> bool:
    """Return whether value matches a date or date-time format; raise on any other format."""
    parse = {"date": date.fromisoformat, "date-time": datetime.fromisoformat}.get(fmt)
    if parse is None:
        msg = f"validator does not support format {fmt!r}"
        raise NotImplementedError(msg)
    if fmt == "date-time" and "T" not in value:
        return False
    try:
        parse(value)
    except ValueError:
        return False
    return True


def as_schema(node: Json) -> Schema:
    """Return node as a schema object, or raise when the schema file is malformed."""
    if not isinstance(node, Mapping):
        msg = f"expected a schema object, got {node!r}"
        raise TypeError(msg)
    return node


def _as_list(node: Json) -> Sequence[Json]:
    """Return node as a JSON array, or raise when the schema file is malformed."""
    if isinstance(node, str) or not isinstance(node, Sequence):
        msg = f"expected a JSON array, got {node!r}"
        raise TypeError(msg)
    return node


def _object_errors(value: Mapping[str, Json], schema: Schema, path: str) -> list[str]:
    """Return the errors from the object keywords: required, minProperties, properties, extras."""
    required = _as_list(schema.get("required", []))
    errors = [f"{path}: missing {key!r}" for key in required if str(key) not in value]
    min_properties = schema.get("minProperties")
    if isinstance(min_properties, int) and len(value) < min_properties:
        errors.append(f"{path}: fewer than {min_properties} properties")
    properties = as_schema(schema.get("properties", {}))
    extra = schema.get("additionalProperties", True)
    for key, item in value.items():
        if key in properties:
            errors += validate(item, as_schema(properties[key]), f"{path}.{key}")
        elif extra is False:
            errors.append(f"{path}: unexpected property {key!r}")
        elif isinstance(extra, Mapping):
            errors += validate(item, extra, f"{path}.{key}")
    return errors


def _scalar_errors(value: Json, schema: Schema, path: str) -> list[str]:
    """Return the errors from the number and string keywords."""
    errors: list[str] = []
    if isinstance(value, int | float) and not isinstance(value, bool):
        low, high = schema.get("minimum"), schema.get("maximum")
        if isinstance(low, int | float) and value < low:
            errors.append(f"{path}: {value} is below {low}")
        if isinstance(high, int | float) and value > high:
            errors.append(f"{path}: {value} is above {high}")
    if isinstance(value, str):
        min_length, pattern, fmt = (schema.get(k) for k in ("minLength", "pattern", "format"))
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path}: shorter than {min_length}")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            errors.append(f"{path}: {value!r} does not match {pattern!r}")
        if isinstance(fmt, str) and not _format_ok(value, fmt):
            errors.append(f"{path}: {value!r} is not a {fmt}")
    return errors


def validate(value: Json, schema: Schema, path: str = "$") -> list[str]:
    """Return every error in value against schema; an empty list means value is valid."""
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        msg = f"{path}: validator does not support {sorted(unknown)}"
        raise NotImplementedError(msg)
    types = schema.get("type")
    names = [types] if isinstance(types, str) else list(_as_list(types or []))
    if names and not any(_has_type(value, str(n)) for n in names):
        return [f"{path}: {_type_of(value)} is not {names}"]
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: {value!r} is not {schema['const']!r}")
    if "enum" in schema and value not in _as_list(schema["enum"]):
        errors.append(f"{path}: {value!r} is not one of {schema['enum']!r}")
    if isinstance(value, Mapping):
        errors += _object_errors(value, schema, path)
    if isinstance(value, Sequence) and not isinstance(value, str) and "items" in schema:
        items = as_schema(schema["items"])
        for i, item in enumerate(value):
            errors += validate(item, items, f"{path}[{i}]")
    errors += _scalar_errors(value, schema, path)
    if "if" in schema:
        branch = "then" if not validate(value, as_schema(schema["if"]), path) else "else"
        if branch in schema:
            errors += validate(value, as_schema(schema[branch]), path)
    for sub in _as_list(schema.get("allOf", [])):
        errors += validate(value, as_schema(sub), path)
    return errors


def load_schema(path: Path) -> Schema:
    """Return the parsed JSON object in path."""
    return as_schema(json.loads(path.read_text(encoding="utf-8")))
