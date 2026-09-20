"""Audio utilities, framing, voice activity detection, and ultrasonic watermarking package."""

from .framing import (
    AudioChunker,
    AudioResampler,
    float32_to_pcm_s16le,
    pcm_s16le_to_float32,
)
from .ingestion import AudioIngestionPipeline
from .vad import (
    BaseVAD,
    EnergyVAD,
    SileroVADAdapter,
    SpeechSegment,
    SpeechSegmenter,
    VADResult,
)
from .watermark import detect_watermark, embed_watermark

__all__ = [
    "AudioChunker",
    "AudioIngestionPipeline",
    "AudioResampler",
    "BaseVAD",
    "EnergyVAD",
    "SileroVADAdapter",
    "SpeechSegment",
    "SpeechSegmenter",
    "VADResult",
    "detect_watermark",
    "embed_watermark",
    "float32_to_pcm_s16le",
    "pcm_s16le_to_float32",
]
