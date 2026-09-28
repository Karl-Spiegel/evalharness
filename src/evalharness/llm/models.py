"""Every model ID this project uses. Nothing else names a model.

Verified 2026-09-25 against platform.claude.com/docs/en/models/overview. Re-check before a
release; this list moves in weeks.
"""

from typing import Final, Literal

type ModelKey = Literal["default", "hard", "fast"]

MODELS: Final[dict[ModelKey, str]] = {
    # Default for production work. Thinks by default; effort defaults to "medium".
    "default": "claude-opus-5-5",
    # Hardest reasoning and longest-horizon tasks. Always thinks; needs a refusal fallback.
    "hard": "claude-fable-5-1",
    # Cheap and fast: classification, routing, judges.
    "fast": "claude-haiku-4-5",
}
