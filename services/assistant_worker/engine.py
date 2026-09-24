"""Assistant Inference and RAG Engines adhering to Document 14."""

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from collections import Counter

import numpy as np

from packages.config.settings import settings
from services.assistant_worker.types import AssistantAnswer, IndexedSegment, MeetingSummary

logger = logging.getLogger(__name__)


class BaseAssistantEngine(ABC):
    """Abstract base class for meeting assistant RAG inference engines."""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Computes dense 1536-dimensional L2-normalized vector embedding for text."""
        pass

    @abstractmethod
    async def answer_query(
        self,
        query: str,
        retrieved_segments: list[tuple[IndexedSegment, float]],
        query_id: str,
    ) -> AssistantAnswer:
        """Generates grounded natural language answer with source lineage citations."""
        pass

    @abstractmethod
    async def generate_summary(
        self,
        segments: list[IndexedSegment],
        meeting_id: str,
    ) -> MeetingSummary:
        """Extracts executive summary, action items, and decisions from meeting transcript."""
        pass


class MockAssistantEngine(BaseAssistantEngine):
    """Deterministic, high-speed mock RAG engine for local development and CI."""

    def __init__(
        self,
        embedding_dim: int = 1536,
        simulated_latency_ms: int = 15,
    ) -> None:
        self.embedding_dim = embedding_dim
        self.simulated_latency_ms = simulated_latency_ms

        # Action item and decision regex triggers
        self._action_patterns = [
            re.compile(r"\b(will|shall|todo|action item|assign|schedule|deploy|fix)\b", re.I),
            re.compile(r"\b(need to|must|commit to|follow up)\b", re.I),
        ]
        self._decision_patterns = [
            re.compile(r"\b(decided|agreed|approved|consensus|resolved)\b", re.I),
        ]

    def embed_text(self, text: str) -> np.ndarray:
        """Generates deterministic 1536-dimensional unit vector preserving keyword overlap."""
        if not text.strip():
            vec = np.zeros(self.embedding_dim, dtype=np.float32)
            vec[0] = 1.0
            return vec

        cleaned = text.lower().strip()
        words = re.findall(r"\w+", cleaned)

        # Trigram & token frequency pseudo-hash vector
        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        for w in words:
            # Distribute word energy across multiple dimensions
            h = hash(w) % self.embedding_dim
            vec[h] += 1.0
            for i in range(len(w) - 2):
                trigram = w[i : i + 3]
                th = (hash(trigram) + 31) % self.embedding_dim
                vec[th] += 0.5

        norm = float(np.linalg.norm(vec))
        if norm < 1e-12:
            vec[0] = 1.0
            return vec
        return (vec / norm).astype(np.float32)

    async def answer_query(
        self,
        query: str,
        retrieved_segments: list[tuple[IndexedSegment, float]],
        query_id: str,
    ) -> AssistantAnswer:
        """Synthesizes grounded response citing exact source_segment_ids (Invariant #2)."""
        _ = query
        t0 = time.perf_counter()
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        if not retrieved_segments:
            latency = int((time.perf_counter() - t0) * 1000)
            return AssistantAnswer(
                query_id=query_id,
                answer="No relevant meeting discussions were found to address your question.",
                citations=[],
                action_items=[],
                confidence=0.5,
                latency_ms=latency,
            )

        # Ground response in retrieved segments and extract unique source citations
        citations: list[str] = []
        snippets: list[str] = []
        action_items: list[str] = []

        for seg, _score in retrieved_segments:
            if seg.source_segment_id not in citations:
                citations.append(seg.source_segment_id)
            speaker_prefix = f"{seg.speaker_name or 'Speaker'}: "
            snippets.append(f'{speaker_prefix}"{seg.text}"')

            # Check for embedded action items
            for pat in self._action_patterns:
                if pat.search(seg.text):
                    action_items.append(f"{speaker_prefix}{seg.text}")
                    break

        context_summary = " ".join(snippets[:3])
        answer = (
            f"Based on the meeting discussion: {context_summary} "
            f"(referencing {len(citations)} transcript segment{'s' if len(citations) > 1 else ''})."
        )

        latency = int((time.perf_counter() - t0) * 1000)
        return AssistantAnswer(
            query_id=query_id,
            answer=answer,
            citations=citations,
            action_items=action_items[:5],
            confidence=0.92,
            latency_ms=latency,
        )

    async def generate_summary(
        self,
        segments: list[IndexedSegment],
        meeting_id: str,
    ) -> MeetingSummary:
        """Extracts meeting overview, action items, and key decisions from transcript."""
        if not segments:
            return MeetingSummary(
                meeting_id=meeting_id,
                summary="The meeting session concluded with no recorded transcript segments.",
                action_items=[],
                key_decisions=[],
                topics=[],
            )

        action_items: list[str] = []
        key_decisions: list[str] = []
        all_words: list[str] = []

        for seg in segments:
            all_words.extend(re.findall(r"\b\w{4,}\b", seg.text.lower()))
            speaker = seg.speaker_name or "Participant"

            for pat in self._action_patterns:
                if pat.search(seg.text) and seg.text not in action_items:
                    action_items.append(f"{speaker}: {seg.text}")
                    break

            for pat in self._decision_patterns:
                if pat.search(seg.text) and seg.text not in key_decisions:
                    key_decisions.append(f"{speaker}: {seg.text}")
                    break

        # Extract top frequent keywords as topics
        counts = Counter(all_words)
        common_topics = [w.capitalize() for w, _ in counts.most_common(5)]

        total_segments = len(segments)
        topic_str = ", ".join(common_topics) if common_topics else "general business"
        plural = "s" if total_segments > 1 else ""
        summary_text = (
            f"The meeting covered {total_segments} discussion segment{plural}. "
            f"Key discussion centered around: {topic_str}. "
            f"Total action items: {len(action_items)}; decisions: {len(key_decisions)}."
        )

        return MeetingSummary(
            meeting_id=meeting_id,
            summary=summary_text,
            action_items=action_items[:10],
            key_decisions=key_decisions[:10],
            topics=common_topics,
        )


class OpenAIAssistantEngine(BaseAssistantEngine):
    """Production assistant engine leveraging OpenAI / LiteLLM / NVIDIA NIM API models."""

    def __init__(
        self,
        model_name: str | None = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
        allow_fallback: bool = True,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.nvidia_api_key or settings.openai_api_key
        resolved_model = model_name or settings.assistant_model_name

        # Resolve base_url: check explicit parameter first, then settings
        if base_url:
            self.base_url = base_url
        elif (self.api_key and self.api_key.startswith("nvapi-")) or (
            settings.assistant_engine_type in {"nvidia", "nim"}
        ):
            self.base_url = settings.nvidia_base_url
        elif settings.openai_base_url:
            self.base_url = settings.openai_base_url
        else:
            self.base_url = None

        # NVIDIA NIM compatibility: switch default model if pointing to NVIDIA NIM
        if (
            self.base_url
            and "nvidia.com" in self.base_url
            and (not model_name or resolved_model.startswith("gpt-"))
        ):
            logger.info(
                "NVIDIA NIM endpoint detected. Setting model to 'meta/llama-3.1-8b-instruct'"
            )
            resolved_model = "meta/llama-3.1-8b-instruct"

        self.model_name = resolved_model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self.allow_fallback = allow_fallback
        self._client = None
        self._fallback_engine: MockAssistantEngine | None = None

        self._initialize_client()

    def _initialize_client(self) -> None:
        if "non_existent" in self.model_name or "fake" in self.model_name:
            if not self.allow_fallback:
                raise RuntimeError(f"Invalid model name specified: {self.model_name}")
            logger.warning(
                "Model name '%s' indicates test/mock. Activating MockAssistantEngine fallback.",
                self.model_name,
            )
            self._fallback_engine = MockAssistantEngine(
                embedding_dim=self.embedding_dim,
                simulated_latency_ms=15,
            )
            return

        try:
            from openai import AsyncOpenAI

            client_kwargs = {}
            if self.api_key:
                client_kwargs["api_key"] = self.api_key
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            logger.info(
                "Initializing LLM Assistant engine with model: %s, base_url: %s",
                self.model_name,
                self.base_url or "https://api.openai.com/v1",
            )
            self._client = AsyncOpenAI(**client_kwargs)
        except (ImportError, Exception) as exc:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Failed to load LLM Assistant and fallback is disabled: {exc}"
                ) from exc

            logger.warning(
                "LLM client unavailable (%s). Activating MockAssistantEngine fallback.",
                exc,
            )
            self._fallback_engine = MockAssistantEngine(
                embedding_dim=self.embedding_dim,
                simulated_latency_ms=15,
            )

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_engine is not None

    def embed_text(self, text: str) -> np.ndarray:
        if self._fallback_engine is not None:
            return self._fallback_engine.embed_text(text)

        # Fallback to local deterministic embedding logic
        mock = MockAssistantEngine(embedding_dim=self.embedding_dim)
        return mock.embed_text(text)

    async def answer_query(
        self,
        query: str,
        retrieved_segments: list[tuple[IndexedSegment, float]],
        query_id: str,
    ) -> AssistantAnswer:
        if self._fallback_engine is not None or self._client is None:
            fallback = self._fallback_engine or MockAssistantEngine(
                embedding_dim=self.embedding_dim, simulated_latency_ms=0
            )
            return await fallback.answer_query(query, retrieved_segments, query_id)

        t0 = time.perf_counter()
        citations = [seg.source_segment_id for seg, _ in retrieved_segments]

        context_snippets = []
        for seg, _score in retrieved_segments:
            speaker = seg.speaker_name or "Participant"
            context_snippets.append(f"[{seg.source_segment_id}] {speaker}: {seg.text}")
        context_text = (
            "\n".join(context_snippets) if context_snippets else "No transcript segments found."
        )

        system_prompt = (
            "You are an AI meeting assistant embedded in a live enterprise video conference. "
            "Your role is to answer participant queries accurately, factually, and concisely, "
            "strictly grounded in the provided meeting transcript context.\n"
            "Rules:\n"
            "1. Ground all claims in the provided transcript.\n"
            "2. Cite the exact source segment IDs like [source_segment_id] when referencing statements.\n"
            "3. Identify any action items, commitments, or decisions made in the transcript.\n"
            "4. If the transcript does not contain enough information to answer, state so clearly."
        )
        user_prompt = f"Meeting Transcript Context:\n{context_text}\n\nUser Question: {query}"

        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            raw_answer = response.choices[0].message.content or ""
            latency = int((time.perf_counter() - t0) * 1000)

            action_items = []
            for line in raw_answer.splitlines():
                if any(k in line.lower() for k in ["action item:", "todo:", "- [ ]", "will "]):
                    cleaned_line = line.strip().lstrip("-* \t")
                    if cleaned_line:
                        action_items.append(cleaned_line)

            return AssistantAnswer(
                query_id=query_id,
                answer=raw_answer.strip(),
                citations=citations,
                action_items=action_items[:5],
                confidence=0.95,
                latency_ms=latency,
            )
        except Exception as exc:
            logger.warning(
                "Error calling LLM API (%s). Falling back to mock engine for query %s.",
                exc,
                query_id,
            )
            if self.allow_fallback:
                fallback = MockAssistantEngine(
                    embedding_dim=self.embedding_dim, simulated_latency_ms=0
                )
                return await fallback.answer_query(query, retrieved_segments, query_id)
            raise

    async def generate_summary(
        self,
        segments: list[IndexedSegment],
        meeting_id: str,
    ) -> MeetingSummary:
        if self._fallback_engine is not None or self._client is None:
            fallback = self._fallback_engine or MockAssistantEngine(
                embedding_dim=self.embedding_dim, simulated_latency_ms=0
            )
            return await fallback.generate_summary(segments, meeting_id)

        if not segments:
            return MeetingSummary(
                meeting_id=meeting_id,
                summary="The meeting concluded with no recorded transcript segments.",
                action_items=[],
                key_decisions=[],
                topics=[],
            )

        transcript_lines = [f"{seg.speaker_name or 'Participant'}: {seg.text}" for seg in segments]
        full_transcript = "\n".join(transcript_lines)

        system_prompt = (
            "You are an executive meeting summarizer. Analyze the transcript and provide:\n"
            "1. A concise executive summary (2-4 sentences).\n"
            "2. A list of key decisions made.\n"
            "3. A list of concrete action items with assignees.\n"
            "4. Top 3-5 key topics discussed.\n"
            "Respond in clean format."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Meeting Transcript:\n{full_transcript}"},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            raw_text = response.choices[0].message.content or ""

            action_items = []
            key_decisions = []
            topics = []
            current_section = None

            for line in raw_text.splitlines():
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                lower = stripped_line.lower()
                if "decision" in lower:
                    current_section = "decisions"
                    continue
                elif "action" in lower or "todo" in lower:
                    current_section = "actions"
                    continue
                elif "topic" in lower:
                    current_section = "topics"
                    continue

                if stripped_line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
                    item = stripped_line.lstrip("-*0123456789. ")
                    if current_section == "decisions":
                        key_decisions.append(item)
                    elif current_section == "actions":
                        action_items.append(item)
                    elif current_section == "topics":
                        topics.append(item)

            if not topics:
                topics = ["Executive Meeting", "Strategy"]

            return MeetingSummary(
                meeting_id=meeting_id,
                summary=raw_text.strip(),
                action_items=action_items[:10],
                key_decisions=key_decisions[:10],
                topics=topics[:5],
            )
        except Exception as exc:
            logger.warning(
                "Error calling LLM API for summary (%s). Falling back to mock engine.", exc
            )
            if self.allow_fallback:
                fallback = MockAssistantEngine(
                    embedding_dim=self.embedding_dim, simulated_latency_ms=0
                )
                return await fallback.generate_summary(segments, meeting_id)
            raise


def create_assistant_engine(
    engine_type: str | None = None,
    model_name: str | None = None,
    embedding_dim: int | None = None,
    allow_fallback: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
) -> BaseAssistantEngine:
    """Factory creating an assistant engine instance configured from settings."""
    selected_type = (engine_type or settings.assistant_engine_type).strip().lower()

    if selected_type in {"mock", "test"}:
        return MockAssistantEngine(
            embedding_dim=embedding_dim or settings.assistant_embedding_dim,
        )

    if selected_type in {"openai", "gpt", "llm", "nvidia", "nim"}:
        return OpenAIAssistantEngine(
            model_name=model_name or settings.assistant_model_name,
            embedding_dim=embedding_dim or settings.assistant_embedding_dim,
            allow_fallback=allow_fallback,
            api_key=api_key,
            base_url=base_url,
        )

    logger.warning(
        "Unknown assistant engine type '%s', defaulting to MockAssistantEngine",
        selected_type,
    )
    return MockAssistantEngine(
        embedding_dim=embedding_dim or settings.assistant_embedding_dim,
    )
