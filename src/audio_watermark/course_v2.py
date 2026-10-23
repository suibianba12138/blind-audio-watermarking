"""Independent course-facing identity recognition around frozen B1 QIM.

This module is an application-layer wrapper. It does not change the frozen
QIM, payload, carrier selector, or B1 detector. Identity recognition maps one
of four public 32-bit codewords to the existing payload interface and rejects
ambiguous or over-threshold decoded words as UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Literal, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .b1 import CarrierSelector, embed_watermark_b1, _validate_b1_inputs
from .carrier import CarrierGroup
from .detect import _confidence_from_repetitions, _detection_statistic
from .embed import EmbeddingConfig, _validate_audio
from .framing import frame_audio
from .transform import real_fft


IDENTITY_NAMES: tuple[str, ...] = (
    "UESTC-001",
    "UESTC-002",
    "UESTC-003",
    "UESTC-004",
)
BLOCK_SECONDS = 6


def _codeword(a: int, b: int) -> tuple[int, ...]:
    return (a,) * 10 + (b,) * 11 + (a ^ b,) * 11


IDENTITY_CODEBOOK: Mapping[str, tuple[int, ...]] = {
    identity: _codeword(*bits)
    for identity, bits in zip(IDENTITY_NAMES, ((0, 0), (0, 1), (1, 0), (1, 1)))
}


def _validate_binary_sequence(values: Sequence[int], *, name: str) -> tuple[int, ...]:
    normalized = tuple(values)
    if len(normalized) != 32:
        raise ValueError(f"{name} must contain exactly 32 bits")
    if any(
        isinstance(value, bool)
        or not isinstance(value, Integral)
        or int(value) not in (0, 1)
        for value in normalized
    ):
        raise ValueError(f"{name} must contain only 0 and 1")
    return tuple(int(value) for value in normalized)


def hamming_distance(reference: Sequence[int], estimate: Sequence[int]) -> int:
    """Return Hamming distance between two equal-length binary sequences."""

    first = tuple(reference)
    second = tuple(estimate)
    if len(first) != len(second):
        raise ValueError("binary sequences must have the same length")
    if any(
        isinstance(value, bool)
        or not isinstance(value, Integral)
        or int(value) not in (0, 1)
        for value in (*first, *second)
    ):
        raise ValueError("binary sequences must contain only 0 and 1")
    return sum(int(left) != int(right) for left, right in zip(first, second))


def codebook_pairwise_distances() -> dict[tuple[str, str], int]:
    """Return all public codeword pair distances in deterministic order."""

    return {
        (left, right): hamming_distance(
            IDENTITY_CODEBOOK[left], IDENTITY_CODEBOOK[right]
        )
        for index, left in enumerate(IDENTITY_NAMES)
        for right in IDENTITY_NAMES[index + 1 :]
    }


CODEBOOK_MIN_DISTANCE = min(codebook_pairwise_distances().values())


def identity_codeword(identity: str) -> tuple[int, ...]:
    """Return the fixed public 32-bit codeword for one identity."""

    try:
        return IDENTITY_CODEBOOK[identity]
    except KeyError as error:
        raise ValueError(f"unknown identity: {identity}") from error


@dataclass(frozen=True)
class IdentityDecision:
    """Blind identity result with an explicit reject state.

    confidence is a diagnostic normalized nearest-codeword margin, not a
    calibrated probability. It is zero for rejection and ties.
    """

    identity: str | None
    status: Literal["IDENTIFIED", "UNKNOWN"]
    recovered_bits: tuple[int, ...]
    distances: tuple[tuple[str, int], ...]
    minimum_distance: int
    tied: bool
    confidence: float


def identify_bits(
    recovered_bits: Sequence[int],
    *,
    max_hamming_distance: int,
) -> IdentityDecision:
    """Map decoded bits to a legal identity or reject as UNKNOWN."""

    if (
        isinstance(max_hamming_distance, bool)
        or not isinstance(max_hamming_distance, Integral)
        or not 0 <= int(max_hamming_distance) <= 32
    ):
        raise ValueError("max_hamming_distance must be a non-negative integer <= 32")
    bits = _validate_binary_sequence(recovered_bits, name="recovered_bits")
    distances = tuple(
        (identity, hamming_distance(bits, IDENTITY_CODEBOOK[identity]))
        for identity in IDENTITY_NAMES
    )
    minimum_distance = min(distance for _, distance in distances)
    nearest = tuple(
        identity for identity, distance in distances if distance == minimum_distance
    )
    tied = len(nearest) != 1
    second_distance = min(
        distance for identity, distance in distances if identity != nearest[0]
    )
    margin = max(0, second_distance - minimum_distance)
    confidence = (
        margin / 32.0
        if not tied and minimum_distance <= max_hamming_distance
        else 0.0
    )
    accepted = not tied and minimum_distance <= max_hamming_distance
    return IdentityDecision(
        identity=nearest[0] if accepted else None,
        status="IDENTIFIED" if accepted else "UNKNOWN",
        recovered_bits=bits,
        distances=distances,
        minimum_distance=minimum_distance,
        tied=tied,
        confidence=float(confidence),
    )


@dataclass(frozen=True)
class OffsetSelector:
    """Adapt a public selector to a deterministic global frame offset."""

    base: CarrierSelector
    frame_offset: int

    def __post_init__(self) -> None:
        if not callable(getattr(self.base, "group_for_frame", None)):
            raise TypeError("base must provide group_for_frame")
        if (
            isinstance(self.frame_offset, bool)
            or not isinstance(self.frame_offset, Integral)
            or self.frame_offset < 0
        ):
            raise ValueError("frame_offset must be a non-negative integer")

    def group_for_frame(self, frame_index: int) -> CarrierGroup:
        if (
            isinstance(frame_index, bool)
            or not isinstance(frame_index, Integral)
            or frame_index < 0
        ):
            raise ValueError("frame_index must be a non-negative integer")
        return self.base.group_for_frame(self.frame_offset + int(frame_index))


@dataclass(frozen=True)
class BlockEvidence:
    """Per-bit signed evidence recovered from one time block."""

    bit_statistics: tuple[float, ...]
    repetition_statistics: tuple[tuple[float, ...], ...]
    recovered_bits: tuple[int, ...]
    confidence: float


def aggregate_signed_evidence(
    block_statistics: Sequence[Sequence[float]],
) -> tuple[float, ...]:
    """Average signed per-bit evidence across every supplied block."""

    rows = np.asarray(block_statistics, dtype=np.float64)
    if rows.ndim != 2 or rows.shape[0] == 0 or rows.shape[1] == 0:
        raise ValueError("block_statistics must be a non-empty rectangular matrix")
    if not np.all(np.isfinite(rows)):
        raise FloatingPointError("block_statistics must be finite")
    return tuple(float(value) for value in np.mean(rows, axis=0))


def _validate_frame_offset(frame_offset: int) -> int:
    if (
        isinstance(frame_offset, bool)
        or not isinstance(frame_offset, Integral)
        or frame_offset < 0
    ):
        raise ValueError("frame_offset must be a non-negative integer")
    return int(frame_offset)


def embed_identity(
    audio: ArrayLike,
    identity: str,
    config: EmbeddingConfig,
    selector: CarrierSelector,
    *,
    frame_offset: int = 0,
) -> NDArray[np.float64]:
    """Embed one fixed identity using the unchanged B1 payload path."""

    payload = identity_codeword(identity)
    offset_selector = OffsetSelector(selector, _validate_frame_offset(frame_offset))
    return embed_watermark_b1(audio, payload, config, offset_selector)


def detect_block_evidence(
    audio: ArrayLike,
    config: EmbeddingConfig,
    selector: CarrierSelector,
    *,
    frame_offset: int = 0,
) -> BlockEvidence:
    """Recover signed B1 evidence from received audio without an identity label."""

    _validate_b1_inputs(config, selector)
    if config.strength == 0.0:
        raise ValueError("positive strength is required for blind detection")
    samples = _validate_audio(audio)
    offset_selector = OffsetSelector(selector, _validate_frame_offset(frame_offset))
    frames = frame_audio(
        samples,
        frame_length=config.n_fft,
        hop_length=config.hop_length,
        window=config.window,
        pad_end=True,
    )
    required_frames = config.payload_bits * config.frames_per_bit
    if frames.shape[0] < required_frames:
        raise ValueError("audio does not have enough framing capacity for payload")
    spectra = real_fft(frames)

    recovered: list[int] = []
    repetition_statistics: list[tuple[float, ...]] = []
    bit_statistics: list[float] = []
    for bit_index in range(config.payload_bits):
        repetitions = tuple(
            _detection_statistic(
                spectra[bit_index * config.frames_per_bit + repetition],
                offset_selector.group_for_frame(
                    bit_index * config.frames_per_bit + repetition
                ),
                config.strength,
            )
            for repetition in range(config.frames_per_bit)
        )
        statistic = float(np.mean(repetitions))
        repetition_statistics.append(repetitions)
        bit_statistics.append(statistic)
        recovered.append(int(statistic >= 0.0))
    confidence = _confidence_from_repetitions(repetition_statistics)
    if not np.isfinite(confidence):
        raise FloatingPointError("course V2 detection produced non-finite confidence")
    return BlockEvidence(
        bit_statistics=tuple(bit_statistics),
        repetition_statistics=tuple(repetition_statistics),
        recovered_bits=tuple(recovered),
        confidence=float(confidence),
    )


def detect_identity(
    audio: ArrayLike,
    config: EmbeddingConfig,
    selector: CarrierSelector,
    *,
    max_hamming_distance: int,
    frame_offset: int = 0,
) -> IdentityDecision:
    """Blindly identify one block or return UNKNOWN."""

    evidence = detect_block_evidence(
        audio,
        config,
        selector,
        frame_offset=frame_offset,
    )
    return identify_bits(
        evidence.recovered_bits,
        max_hamming_distance=max_hamming_distance,
    )


@dataclass(frozen=True)
class BlockRange:
    """One hop-aligned block range in the original waveform."""

    index: int
    start_sample: int
    stop_sample: int
    frame_offset: int


@dataclass(frozen=True)
class MultiBlockEmbedding:
    """Marked waveform and every block actually modified."""

    audio: NDArray[np.float64]
    blocks: tuple[BlockRange, ...]


@dataclass(frozen=True)
class MultiBlockDecision:
    """Per-block and all-block signed-evidence identity decisions."""

    aggregate: IdentityDecision
    block_decisions: tuple[IdentityDecision, ...]
    block_evidence: tuple[BlockEvidence, ...]
    blocks: tuple[BlockRange, ...]


def full_block_ranges(
    sample_count: int,
    sample_rate: int,
    *,
    block_seconds: int = BLOCK_SECONDS,
    hop_length: int = 2048,
) -> tuple[BlockRange, ...]:
    """Return complete hop-aligned protocol blocks."""

    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, Integral)
        or sample_count <= 0
    ):
        raise ValueError("sample_count must be a positive integer")
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, Integral)
        or sample_rate <= 0
    ):
        raise ValueError("sample_rate must be a positive integer")
    if (
        isinstance(block_seconds, bool)
        or not isinstance(block_seconds, Integral)
        or block_seconds <= 0
    ):
        raise ValueError("block_seconds must be a positive integer")
    if (
        isinstance(hop_length, bool)
        or not isinstance(hop_length, Integral)
        or hop_length <= 0
    ):
        raise ValueError("hop_length must be a positive integer")

    block_samples = int(round(block_seconds * sample_rate))
    step_samples = (
        int(block_seconds * sample_rate // hop_length) * hop_length
    )
    if step_samples <= 0:
        raise ValueError("block duration must span at least one hop")
    blocks: list[BlockRange] = []
    index = 0
    while True:
        start = index * step_samples
        stop = start + block_samples
        if stop > sample_count:
            break
        blocks.append(
            BlockRange(
                index=index,
                start_sample=start,
                stop_sample=stop,
                frame_offset=start // hop_length,
            )
        )
        index += 1
    if not blocks:
        raise ValueError("audio does not contain one complete protocol block")
    return tuple(blocks)


def embed_identity_multiblock(
    audio: ArrayLike,
    identity: str,
    config: EmbeddingConfig,
    selector: CarrierSelector,
    *,
    block_seconds: int = BLOCK_SECONDS,
) -> MultiBlockEmbedding:
    """Embed the same identity in every complete protocol block."""

    samples = _validate_audio(audio)
    blocks = full_block_ranges(
        samples.size,
        config.sample_rate,
        block_seconds=block_seconds,
        hop_length=config.hop_length,
    )
    marked = samples.copy()
    for block in blocks:
        marked[block.start_sample : block.stop_sample] = embed_identity(
            samples[block.start_sample : block.stop_sample],
            identity,
            config,
            selector,
            frame_offset=block.frame_offset,
        )
    return MultiBlockEmbedding(audio=marked, blocks=blocks)


def detect_identity_multiblock(
    audio: ArrayLike,
    config: EmbeddingConfig,
    selector: CarrierSelector,
    *,
    max_hamming_distance: int,
    block_seconds: int = BLOCK_SECONDS,
) -> MultiBlockDecision:
    """Fuse every complete block with equal-weight signed evidence."""

    samples = _validate_audio(audio)
    blocks = full_block_ranges(
        samples.size,
        config.sample_rate,
        block_seconds=block_seconds,
        hop_length=config.hop_length,
    )
    evidence = tuple(
        detect_block_evidence(
            samples[block.start_sample : block.stop_sample],
            config,
            selector,
            frame_offset=block.frame_offset,
        )
        for block in blocks
    )
    block_decisions = tuple(
        identify_bits(item.recovered_bits, max_hamming_distance=max_hamming_distance)
        for item in evidence
    )
    aggregate_statistics = aggregate_signed_evidence(
        [item.bit_statistics for item in evidence]
    )
    aggregate_bits = tuple(int(value >= 0.0) for value in aggregate_statistics)
    aggregate = identify_bits(
        aggregate_bits,
        max_hamming_distance=max_hamming_distance,
    )
    return MultiBlockDecision(
        aggregate=aggregate,
        block_decisions=block_decisions,
        block_evidence=evidence,
        blocks=blocks,
    )
