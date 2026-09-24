"""Contextual Sliding Window Buffer for Discourse Coherence adhering to Document 14."""

from collections import deque


class ContextWindowBuffer:
    """Maintains a sliding FIFO queue of preceding utterances per participant in a meeting."""

    def __init__(self, max_sentences: int = 2) -> None:
        self.max_sentences = max_sentences
        self._buffers: dict[tuple[str, str], deque[str]] = {}

    def _get_key(self, meeting_id: str, participant_id: str) -> tuple[str, str]:
        return meeting_id, participant_id

    def add_utterance(self, meeting_id: str, participant_id: str, text: str) -> None:
        """Appends a completed utterance to the speaker's sliding context window."""
        cleaned = text.strip()
        if not cleaned:
            return

        key = self._get_key(meeting_id, participant_id)
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self.max_sentences)

        self._buffers[key].append(cleaned)

    def get_context(self, meeting_id: str, participant_id: str) -> list[str]:
        """Retrieves preceding context utterances for the speaker."""
        key = self._get_key(meeting_id, participant_id)
        if key not in self._buffers:
            return []
        return list(self._buffers[key])

    def format_context_prefix(
        self,
        meeting_id: str,
        participant_id: str,
        current_text: str,
    ) -> str:
        """Formats discourse context prepended to the current utterance."""
        context = self.get_context(meeting_id, participant_id)
        if not context:
            return current_text
        context_str = " ".join(context)
        return f"{context_str} {current_text}"

    def clear_meeting(self, meeting_id: str) -> None:
        """Purges all context buffers associated with a completed meeting."""
        keys_to_remove = [k for k in self._buffers if k[0] == meeting_id]
        for k in keys_to_remove:
            self._buffers.pop(k, None)

    def clear_participant(self, meeting_id: str, participant_id: str) -> None:
        """Purges context buffer for a specific participant."""
        key = self._get_key(meeting_id, participant_id)
        self._buffers.pop(key, None)
