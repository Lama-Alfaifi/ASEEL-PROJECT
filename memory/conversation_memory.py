from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationMemory:
    """
    Stores important context from the current conversation.

    This is not a full chat-history store.
    It keeps only useful context that can help interpret follow-up questions.
    """

    context: dict[str, Any] = field(default_factory=dict)

    def get_context(self) -> dict[str, Any]:
        """Return the current conversation context."""
        return self.context.copy()

    def update_context(self, new_context: dict[str, Any]) -> None:
        """
        Update memory without overwriting useful existing values
        with empty or None values.
        """

        for key, value in new_context.items():

            if value is None:
                continue

            if value == "":
                continue

            if value == []:
                continue

            self.context[key] = value

    def clear_context(self) -> None:
        """Clear the conversation memory."""
        self.context.clear()

    def to_prompt_context(self) -> str:
        """Convert memory into a simple context string for the workflow."""

        if not self.context:
            return ""

        parts = []

        for key, value in self.context.items():
            parts.append(f"{key}: {value}")

        return "\n".join(parts)