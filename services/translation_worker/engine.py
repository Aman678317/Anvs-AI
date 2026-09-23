"""Neural Machine Translation (NMT) Inference Engines adhering to Document 14."""

import asyncio
import logging
import sys
import time
from abc import ABC, abstractmethod

from packages.config.settings import settings
from packages.language_registry import get_optimal_nmt_model, normalize_code
from services.translation_worker.languages import iso639_3_to_nllb
from services.translation_worker.types import TranslationResult

logger = logging.getLogger(__name__)


class BaseNMTEngine(ABC):
    """Abstract base class for neural machine translation inference engines."""

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: list[str] | None = None,
    ) -> TranslationResult:
        """Translates text from source language to target language."""
        pass

    async def translate_batch(
        self,
        text: str,
        source_lang: str,
        target_languages: list[str],
        context: list[str] | None = None,
    ) -> list[TranslationResult]:
        """Translates text into multiple target languages concurrently."""
        tasks = [
            self.translate(text, source_lang, tgt, context)
            for tgt in target_languages
            if normalize_code(tgt) != normalize_code(source_lang)
        ]
        if not tasks:
            return []
        return await asyncio.gather(*tasks)


class MockNMTEngine(BaseNMTEngine):
    """Deterministic, high-speed mock translation engine for local testing and CI."""

    def __init__(self, simulated_latency_ms: int = 15) -> None:
        self.simulated_latency_ms = simulated_latency_ms
        # High-frequency meeting phrase translations (eng -> target)
        self._phrase_dict: dict[tuple[str, str], dict[str, str]] = {
            ("eng", "spa"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "Bienvenidos a todos a nuestra reunión multilingüe, comencemos la revisión."
                ),
                "hello world contract verification": "Hola mundo verificación de contrato",
                "can everyone hear me clearly?": "¿Todos me escuchan con claridad?",
                "thank you for joining today's session.": "Gracias por unirse a la sesión de hoy.",
                "good morning everyone": "Buenos días a todos",
            },
            ("eng", "fra"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "Bienvenue à tous à notre réunion multilingue, commençons la révision."
                ),
                "hello world contract verification": "Bonjour le monde vérification du contrat",
                "can everyone hear me clearly?": "Est-ce que tout le monde m'entend clairement?",
                "thank you for joining today's session.": (
                    "Merci d'avoir rejoint la session d'aujourd'hui."
                ),
            },
            ("eng", "deu"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "Willkommen alle zu unserem mehrsprachigen Treffen, "
                    "beginnen wir die Überprüfung."
                ),
                "hello world contract verification": "Hallo Welt Vertragsüberprüfung",
                "can everyone hear me clearly?": "Können mich alle deutlich hören?",
                "thank you for joining today's session.": (
                    "Vielen Dank für Ihre Teilnahme an der heutigen Sitzung."
                ),
            },
            ("eng", "zho"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "欢迎大家参加我们的多语言会议，让我们开始审查。"
                ),
                "hello world contract verification": "你好世界合约验证",
                "can everyone hear me clearly?": "大家能听清我的声音吗？",
                "thank you for joining today's session.": "感谢大家参加今天的会议。",
            },
            ("eng", "jpn"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "多言語ミーティングへようこそ、レビューを開始しましょう。"
                ),
                "hello world contract verification": "ハローワールド契約検証",
                "can everyone hear me clearly?": "皆様、私の声がはっきりと聞こえますか？",
                "thank you for joining today's session.": "本日のセッションにご参加いただきありがとうございます。",
            },
            ("eng", "hin"): {
                "welcome everyone to our multilingual meeting, let's begin the review.": (
                    "हमारी बहुभाषी बैठक में आप सभी का स्वागत है, आइए समीक्षा शुरू करें।"
                ),
                "hello world contract verification": "नमस्ते दुनिया अनुबंध सत्यापन",
                "can everyone hear me clearly?": "क्या हर कोई मुझे स्पष्ट रूप से सुन सकता है?",
            },
        }

        # Language name prefixes for generic generative fallback
        self._lang_prefixes: dict[str, str] = {
            "spa": "[ES]",
            "fra": "[FR]",
            "deu": "[DE]",
            "zho": "[ZH]",
            "jpn": "[JA]",
            "hin": "[HI]",
            "por": "[PT]",
            "rus": "[RU]",
            "ara": "[AR]",
            "ita": "[IT]",
            "kor": "[KO]",
            "nld": "[NL]",
            "tur": "[TR]",
        }

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: list[str] | None = None,
    ) -> TranslationResult:
        _ = context
        src = normalize_code(source_lang)
        tgt = normalize_code(target_lang)
        cleaned_text = text.strip()

        t0 = time.perf_counter()
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        # 1. Identity translation
        if src == tgt:
            latency = int((time.perf_counter() - t0) * 1000)
            return TranslationResult(
                translated_text=cleaned_text,
                source_language=src,
                target_language=tgt,
                latency_ms=latency,
                model_version="mock-nmt-passthrough",
            )

        # 2. Known dictionary lookup
        lookup_key = (src, tgt)
        lower_text = cleaned_text.lower()
        if lookup_key in self._phrase_dict and lower_text in self._phrase_dict[lookup_key]:
            translated = self._phrase_dict[lookup_key][lower_text]
        else:
            # 3. Deterministic lexical transformation preserving sentence structure
            prefix = self._lang_prefixes.get(tgt, f"[{tgt.upper()}]")
            translated = f"{prefix} {cleaned_text}"

        latency = int((time.perf_counter() - t0) * 1000)
        return TranslationResult(
            translated_text=translated,
            source_language=src,
            target_language=tgt,
            latency_ms=latency,
            model_version=f"mock-{get_optimal_nmt_model(src, tgt)}",
        )


class NLLBTranslationEngine(BaseNMTEngine):
    """Production NMT engine using Meta NLLB-200-distilled-600M via Hugging Face."""

    def __init__(
        self,
        model_name: str = "facebook/nllb-200-distilled-600M",
        device: str = "cpu",
        allow_fallback: bool = True,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.allow_fallback = allow_fallback
        self._tokenizer = None
        self._model = None
        self._fallback_engine: MockNMTEngine | None = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        if sys.version_info >= (3, 14) and sys.platform == "win32":
            logger.info("Python 3.14 on Windows detected: activating MockNMTEngine fallback")
            self._fallback_engine = MockNMTEngine(simulated_latency_ms=15)
            return

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            logger.info("Initializing NLLB model: %s on %s", self.model_name, self.device)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            if self.device != "cpu":
                self._model = self._model.to(self.device)
        except (ImportError, Exception) as exc:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Failed to load NLLB model '{self.model_name}' and fallback is disabled: {exc}"
                ) from exc

            logger.warning("NLLB model unavailable (%s). Activating MockNMTEngine fallback.", exc)
            self._fallback_engine = MockNMTEngine(simulated_latency_ms=15)

    @property
    def is_using_fallback(self) -> bool:
        return self._fallback_engine is not None

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: list[str] | None = None,
    ) -> TranslationResult:
        if self._fallback_engine is not None:
            return await self._fallback_engine.translate(text, source_lang, target_lang, context)

        src = normalize_code(source_lang)
        tgt = normalize_code(target_lang)

        if src == tgt:
            return TranslationResult(
                translated_text=text.strip(),
                source_language=src,
                target_language=tgt,
                latency_ms=0,
                model_version=f"{self.model_name}-passthrough",
            )

        src_nllb = iso639_3_to_nllb(src)
        tgt_nllb = iso639_3_to_nllb(tgt)

        # Contextual prefix integration
        input_text = f"{' '.join(context)} {text}" if context else text

        loop = asyncio.get_running_loop()
        t0 = time.perf_counter()

        def _infer() -> str:
            self._tokenizer.src_lang = src_nllb
            inputs = self._tokenizer(input_text, return_tensors="pt")
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            tgt_lang_id = self._tokenizer.lang_code_to_id[tgt_nllb]
            outputs = self._model.generate(
                **inputs,
                forced_bos_token_id=tgt_lang_id,
                max_length=512,
            )
            decoded = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
            return decoded[0].strip() if decoded else ""

        translated_output = await loop.run_in_executor(None, _infer)
        latency = int((time.perf_counter() - t0) * 1000)

        return TranslationResult(
            translated_text=translated_output,
            source_language=src,
            target_language=tgt,
            latency_ms=latency,
            model_version=self.model_name,
        )


def create_nmt_engine(
    engine_type: str | None = None,
    model_name: str | None = None,
    device: str | None = None,
    allow_fallback: bool = True,
) -> BaseNMTEngine:
    """Factory creating an NMT engine instance configured from settings or parameters."""
    selected_type = (engine_type or settings.nmt_engine_type).strip().lower()

    if selected_type in {"mock", "test"}:
        return MockNMTEngine()

    if selected_type in {"nllb", "transformers"}:
        return NLLBTranslationEngine(
            model_name=model_name or settings.nmt_model_name,
            device=device or settings.nmt_device,
            allow_fallback=allow_fallback,
        )

    logger.warning("Unknown NMT engine type '%s', defaulting to MockNMTEngine", selected_type)
    return MockNMTEngine()
