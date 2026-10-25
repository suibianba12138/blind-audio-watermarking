"""Blind public API for the frozen V3 8-bit Soft-Code candidate.

This module is deliberately a narrow adapter.  It owns input preparation,
message validation, and conversion between the public integer API and the
frozen 32-position B1 channel; it does not implement a second watermarking
algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from numbers import Integral
from typing import Mapping

from audio_watermark.b1 import embed_watermark_b1
from audio_watermark.b1_soft import detect_watermark_b1_soft
from audio_watermark.b2_capacity import decode_soft_capacity, encode_capacity_payload
from audio_watermark.embed import EmbeddingConfig

from .audio_io import AudioData, TARGET_SAMPLE_RATE, prepare_for_demo
from .public_config import build_embedding_config, load_public_selector


V3_STRENGTH = 1.60
V3_PRESENCE_THRESHOLD = 0.7855073980199624
V3_PAYLOAD_BITS = 8
V3_PHYSICAL_BITS = 32
V3_DURATION_SECONDS = 6
V3_SELECTOR = "REAL_TOP32"
V3_WATERMARK_SEED = 7
VALID_STATUSES = frozenset({"IDENTIFIED", "UNKNOWN"})


@dataclass(frozen=True)
class V3EmbedResult:
    """Prepared marked audio and non-sensitive V3 embedding metadata."""

    audio: AudioData
    message: int
    duration_seconds: float
    sample_rate: int
    provenance: Mapping[str, object]


@dataclass(frozen=True)
class V3DetectionResult:
    """Blind V3 decision and diagnostic score from received audio only."""

    status: str
    message: int | None
    presence_score: float
    threshold: float
    margin: float
    duration_seconds: float
    sample_rate: int
    provenance: Mapping[str, object]


def _v3_config() -> EmbeddingConfig:
    """Return the V3 adapter config without changing Course V2 config."""

    return replace(build_embedding_config(), strength=V3_STRENGTH)


def _prepare_v3_audio(audio: AudioData) -> AudioData:
    if not isinstance(audio, AudioData):
        raise ValueError("audio must be an AudioData instance")
    return prepare_for_demo(
        audio,
        duration_seconds=V3_DURATION_SECONDS,
        target_sample_rate=TARGET_SAMPLE_RATE,
    )


def _provenance() -> dict[str, object]:
    """Return explicitly V3-scoped public metadata."""

    return {
        "system": "V3 8-bit Soft-Code",
        "selector": V3_SELECTOR,
        "watermark_seed": V3_WATERMARK_SEED,
        "strength": V3_STRENGTH,
        "presence_threshold": V3_PRESENCE_THRESHOLD,
        "effective_payload_bits": V3_PAYLOAD_BITS,
        "physical_payload_bits": V3_PHYSICAL_BITS,
        "duration_seconds": V3_DURATION_SECONDS,
        "sample_rate_hz": TARGET_SAMPLE_RATE,
    }


def _message_bits(message: int) -> tuple[int, ...]:
    if isinstance(message, bool) or not isinstance(message, Integral):
        raise ValueError("message must be an integer in the range [0, 255]")
    value = int(message)
    if not 0 <= value <= 255:
        raise ValueError("message must be an integer in the range [0, 255]")
    return tuple((value >> (7 - bit)) & 1 for bit in range(V3_PAYLOAD_BITS))


def embed_message(audio: AudioData, message: int) -> V3EmbedResult:
    """Embed one integer message in the frozen six-second V3 block."""

    prepared = _prepare_v3_audio(audio)
    bits = _message_bits(message)
    value = int(message)
    config = _v3_config()
    selector = load_public_selector()
    physical_payload = encode_capacity_payload(bits, V3_PAYLOAD_BITS)
    marked_samples = embed_watermark_b1(
        prepared.samples,
        physical_payload,
        config,
        selector,
    )
    marked = AudioData(marked_samples, prepared.sample_rate)
    return V3EmbedResult(
        audio=marked,
        message=value,
        duration_seconds=marked.samples.size / marked.sample_rate,
        sample_rate=marked.sample_rate,
        provenance=_provenance(),
    )


def detect_message(audio: AudioData) -> V3DetectionResult:
    """Blindly detect one V3 message from received audio."""

    prepared = _prepare_v3_audio(audio)
    config = _v3_config()
    selector = load_public_selector()
    detection = detect_watermark_b1_soft(prepared.samples, config, selector)
    decoded = decode_soft_capacity(detection.physical_statistics, V3_PAYLOAD_BITS)
    accepted = decoded.presence_score >= V3_PRESENCE_THRESHOLD
    status = "IDENTIFIED" if accepted else "UNKNOWN"
    message = (
        int("".join(str(bit) for bit in decoded.message_bits), 2) if accepted else None
    )
    if status not in VALID_STATUSES:
        raise RuntimeError("V3 detector produced an invalid status")
    return V3DetectionResult(
        status=status,
        message=message,
        presence_score=float(decoded.presence_score),
        threshold=V3_PRESENCE_THRESHOLD,
        margin=float(decoded.margin),
        duration_seconds=prepared.samples.size / prepared.sample_rate,
        sample_rate=prepared.sample_rate,
        provenance=_provenance(),
    )
