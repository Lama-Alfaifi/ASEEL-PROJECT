from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationMemory:
    """
    Stores adaptive context from the current conversation.

    This is not a full chat-history store.
    It keeps useful trip context such as destination,
    region, occasion, current topic, and topics discussed.
    """

    context: dict[str, Any] = field(
        default_factory=lambda: {
            "destination": None,
            "region": None,
            "user_role": None,
            "occasion": None,
            "first_time": None,
            "current_topic": None,
            "topics_discussed": [],
        }
    )

    def get_context(self) -> dict[str, Any]:
        """Return the current conversation context."""
        return self.context.copy()

    def update_context(
        self,
        new_context: dict[str, Any],
    ) -> None:
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

            if key == "topics_discussed":

                existing_topics = self.context.get(
                    "topics_discussed",
                    [],
                )

                if not isinstance(existing_topics, list):
                    existing_topics = []

                if isinstance(value, list):

                    for topic in value:
                        if (
                            topic
                            and topic not in existing_topics
                        ):
                            existing_topics.append(topic)

                elif value not in existing_topics:
                    existing_topics.append(value)

                self.context["topics_discussed"] = existing_topics

            else:
                self.context[key] = value

        # Keep the current topic synchronized
        # with the latest category.
        if new_context.get("category"):
            self.context["current_topic"] = new_context["category"]

    def clear_context(self) -> None:
        """Clear the conversation memory."""
        self.context = {
            "destination": None,
            "region": None,
            "user_role": None,
            "occasion": None,
            "first_time": None,
            "current_topic": None,
            "topics_discussed": [],
        }

    def to_prompt_context(self) -> str:
        """
        Convert adaptive memory into context
        that can be provided to the workflow.
        """

        if not self.context:
            return ""

        parts = []

        for key, value in self.context.items():

            if value is None:
                continue

            if value == "":
                continue

            if value == []:
                continue

            parts.append(f"{key}: {value}")

        return "\n".join(parts)