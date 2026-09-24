"""Meeting Stream Summarizer for incremental transcript summaries (PR-12).

Maintains a rolling summary of a live meeting by batching indexed transcript
segments and generating intermediate summaries at configurable watermarks.
On meeting end, produces a final executive summary with action items and decisions.
"""

import logging
from dataclasses import dataclass, field

from services.assistant_worker.engine import BaseAssistantEngine
from services.assistant_worker.types import IndexedSegment, MeetingSummary

logger = logging.getLogger(__name__)

_DEFAULT_BATCH_WATERMARK = 50
_DEFAULT_MIN_SEGMENTS_FOR_SUMMARY = 3


@dataclass
class RollingSummaryState:
    """Mutable state tracking incremental segment batches and intermediate summaries."""

    meeting_id: str
    tenant_id: str
    batch_watermark: int = _DEFAULT_BATCH_WATERMARK
    segments_since_last_summary: list[IndexedSegment] = field(default_factory=list)
    all_segments: list[IndexedSegment] = field(default_factory=list)
    intermediate_summaries: list[str] = field(default_factory=list)
    summaries_generated: int = 0


class MeetingStreamSummarizer:
    """Generates rolling intermediate and final executive summaries for a live meeting.

    Lifecycle:
        1. `add_segment()` — called for each indexed transcript segment.
           Triggers an intermediate batch summary every `batch_watermark` segments.
        2. `finalize()` — called when the meeting ends (RoomStateEvent: "ended").
           Synthesizes the definitive executive summary across the full transcript.

    Summaries preserve Invariant #2 by tracking all `source_segment_id` values
    that contributed to each generated summary batch.
    """

    def __init__(
        self,
        engine: BaseAssistantEngine,
        meeting_id: str,
        tenant_id: str,
        batch_watermark: int = _DEFAULT_BATCH_WATERMARK,
    ) -> None:
        self.engine = engine
        self._state = RollingSummaryState(
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            batch_watermark=batch_watermark,
        )

    @property
    def meeting_id(self) -> str:
        return self._state.meeting_id

    @property
    def total_segments_indexed(self) -> int:
        return len(self._state.all_segments)

    @property
    def tenant_id(self) -> str:
        return self._state.tenant_id

    @property
    def summaries_generated(self) -> int:
        return self._state.summaries_generated

    def add_segment(self, segment: IndexedSegment) -> None:
        """Registers a new transcript segment and triggers batch summary if watermark reached."""
        self._state.all_segments.append(segment)
        self._state.segments_since_last_summary.append(segment)

    async def maybe_generate_batch_summary(self) -> MeetingSummary | None:
        """Generates an intermediate summary if the batch watermark has been reached.

        Returns the summary if triggered, None otherwise.
        """
        batch = self._state.segments_since_last_summary
        if len(batch) < self._state.batch_watermark:
            return None

        if len(batch) < _DEFAULT_MIN_SEGMENTS_FOR_SUMMARY:
            return None

        logger.info(
            "Generating intermediate summary for meeting %s: %d-segment batch",
            self.meeting_id,
            len(batch),
        )
        summary = await self.engine.generate_summary(
            segments=list(batch),
            meeting_id=self.meeting_id,
        )

        # Record intermediate summary text and reset pending batch
        self._state.intermediate_summaries.append(summary.summary)
        self._state.segments_since_last_summary = []
        self._state.summaries_generated += 1

        logger.info(
            "Intermediate summary #%d generated for meeting %s (%d action items, %d decisions).",
            self._state.summaries_generated,
            self.meeting_id,
            len(summary.action_items),
            len(summary.key_decisions),
        )
        return summary

    async def finalize(self) -> MeetingSummary:
        """Generates the final definitive executive summary for the entire meeting.

        Combines all segments — both those already summarized and any remaining
        pending batch segments — into a unified output.

        Returns:
            Final MeetingSummary with full action items, decisions, and topics.
        """
        all_segs = self._state.all_segments
        logger.info(
            "Finalizing executive summary for meeting %s (%d total segments, %d prior batches).",
            self.meeting_id,
            len(all_segs),
            self._state.summaries_generated,
        )

        if not all_segs:
            return MeetingSummary(
                meeting_id=self.meeting_id,
                summary="The meeting concluded with no recorded transcript content.",
                action_items=[],
                key_decisions=[],
                topics=[],
            )

        summary = await self.engine.generate_summary(
            segments=all_segs,
            meeting_id=self.meeting_id,
        )
        self._state.summaries_generated += 1
        return summary

    def get_source_segment_ids(self) -> list[str]:
        """Returns all source_segment_ids that have contributed to this meeting's summaries."""
        return [seg.source_segment_id for seg in self._state.all_segments]
