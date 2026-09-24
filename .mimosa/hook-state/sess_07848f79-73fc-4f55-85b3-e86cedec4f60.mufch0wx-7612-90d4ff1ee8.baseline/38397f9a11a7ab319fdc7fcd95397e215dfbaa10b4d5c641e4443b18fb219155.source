"""Glossary Registry and In-Context Terminology Protection for Translation Worker."""

import logging
import re

logger = logging.getLogger(__name__)


class GlossaryRegistry:
    """Manages tenant- and meeting-scoped glossaries for preserving technical terminology."""

    def __init__(self) -> None:
        # Key: meeting_id -> dict[source_term_lower, target_term]
        self._meeting_glossaries: dict[str, dict[str, str]] = {}
        # Key: tenant_id -> dict[source_term_lower, target_term]
        self._tenant_glossaries: dict[str, dict[str, str]] = {}

    def set_meeting_glossary(self, meeting_id: str, terms: dict[str, str]) -> None:
        """Configures or overwrites the glossary for a specific meeting."""
        self._meeting_glossaries[meeting_id] = {k.strip(): v.strip() for k, v in terms.items() if k}
        logger.info(
            "Registered %d glossary terms for meeting %s",
            len(self._meeting_glossaries[meeting_id]),
            meeting_id,
        )

    def set_tenant_glossary(self, tenant_id: str, terms: dict[str, str]) -> None:
        """Configures organization-wide default glossary terms."""
        self._tenant_glossaries[tenant_id] = {k.strip(): v.strip() for k, v in terms.items() if k}

    def get_effective_glossary(self, meeting_id: str, tenant_id: str = "") -> dict[str, str]:
        """Returns merged dictionary of tenant and meeting terms (meeting takes precedence)."""
        merged: dict[str, str] = {}
        if tenant_id and tenant_id in self._tenant_glossaries:
            merged.update(self._tenant_glossaries[tenant_id])
        if meeting_id in self._meeting_glossaries:
            merged.update(self._meeting_glossaries[meeting_id])
        return merged

    def apply_glossary_pre(
        self,
        text: str,
        glossary: dict[str, str],
    ) -> tuple[str, dict[str, str]]:
        """Replaces glossary terms with protected token placeholders before MT inference.

        Returns:
            tuple of (protected_text, map_of_placeholder_to_target_term)
        """
        if not glossary or not text:
            return text, {}

        placeholders: dict[str, str] = {}
        processed_text = text

        for i, (src_term, target_term) in enumerate(glossary.items()):
            token = f"__GLOSS_{i}__"
            # Word-boundary match for terms
            pattern = re.compile(rf"\b{re.escape(src_term)}\b", re.IGNORECASE)
            if pattern.search(processed_text):
                processed_text = pattern.sub(token, processed_text)
                placeholders[token] = target_term

        return processed_text, placeholders

    def apply_glossary_post(
        self,
        translated_text: str,
        placeholders: dict[str, str],
    ) -> str:
        """Substitutes protected placeholders back with the authoritative target terms."""
        if not placeholders or not translated_text:
            return translated_text

        result = translated_text
        for token, target_term in placeholders.items():
            result = result.replace(token, target_term)
        return result

    def clear_meeting(self, meeting_id: str) -> None:
        """Purges meeting glossary upon meeting conclusion."""
        self._meeting_glossaries.pop(meeting_id, None)


# Default singleton instance
glossary_registry = GlossaryRegistry()
