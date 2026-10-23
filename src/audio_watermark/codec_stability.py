"""Detector-consistent carrier stability maps for the P3 pilot.

This module is deliberately separate from the frozen B0 carrier selection.
It reuses B0's carrier geometry and ``carrier_sides`` representation, but does
not alter ``carrier_for_frame`` or the blind detector.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from numbers import Integral
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import spearmanr

from .carrier import (
    CarrierGroup,
    FrequencyBand,
    carrier_sides,
    generate_candidate_carriers,
)


STABILITY_FORMULA = (
    "codec_error=median(abs(D_codec-D_clean)); "
    "combined_instability=mean(codec_error); "
    "stability_score=1/(1+combined_instability)"
)


@dataclass(frozen=True)
class StabilityMapEntry:
    """One complete candidate-group entry in a frozen stability map."""

    group_id: int
    seed: int
    a_bins: tuple[int, ...]
    b_bins: tuple[int, ...]
    codec_errors: dict[str, float]
    combined_instability: float
    stability_score: float
    rank: int


@dataclass(frozen=True)
class StabilityMap:
    """Serializable, deterministic P3 calibration output."""

    pool_seed: int
    entries: tuple[StabilityMapEntry, ...]
    codec_names: tuple[str, ...]
    formula: str = STABILITY_FORMULA

    @property
    def sha256(self) -> str:
        """Return a stable hash of the complete map, including all groups."""

        encoded = json.dumps(
            map_to_dict(self), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def generate_codec_stability_pool(
    *,
    sample_rate: int,
    n_fft: int,
    band: FrequencyBand,
    bins_per_group: int,
    patches_per_bit: int,
    pool_size: int,
    pool_seed: int,
) -> tuple[CarrierGroup, ...]:
    """Generate a deterministic pool while preserving B0 A/B geometry.

    Each group is derived from ``[pool_seed, group_id]`` and delegates actual
    bin construction to the existing B0 generator. No test waveform or codec
    output is involved in pool construction.
    """

    _positive_integer(pool_size, "pool_size")
    _nonnegative_integer(pool_seed, "pool_seed")
    groups: list[CarrierGroup] = []
    seen: set[tuple[int, ...]] = set()
    for group_id in range(pool_size):
        derived_seed = int(
            np.random.SeedSequence([pool_seed, group_id]).generate_state(
                1, dtype=np.uint64
            )[0]
        )
        group = generate_candidate_carriers(
            sample_rate=sample_rate,
            n_fft=n_fft,
            band=band,
            bins_per_group=bins_per_group,
            patches_per_bit=patches_per_bit,
            seed=derived_seed,
        )[0]
        if group.bins in seen:
            raise RuntimeError("codec stability pool contains duplicate groups")
        seen.add(group.bins)
        groups.append(group)
    return tuple(groups)


def group_statistic(
    spectrum: ArrayLike, group: CarrierGroup
) -> float:
    """Return the B0 detector's signed log-magnitude group statistic ``D``."""

    values = np.asarray(spectrum, dtype=np.complex128)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("spectrum must be a finite one-dimensional array")
    a_bins, b_bins = carrier_sides(group)
    if max(group.bins) >= values.size:
        raise ValueError("carrier group exceeds spectrum capacity")
    magnitudes = np.maximum(np.abs(values), np.finfo(np.float64).tiny)
    log_magnitudes = np.log(magnitudes)
    return float(np.sum(log_magnitudes[a_bins]) - np.sum(log_magnitudes[b_bins]))


def group_statistic_series(
    spectra: ArrayLike, group: CarrierGroup
) -> NDArray[np.float64]:
    """Return the B0 group statistic for every frame in a spectrum matrix."""

    values = np.asarray(spectra, dtype=np.complex128)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("spectra must be a finite two-dimensional array")
    a_bins, b_bins = carrier_sides(group)
    if max(group.bins) >= values.shape[1]:
        raise ValueError("carrier group exceeds spectrum capacity")
    log_magnitudes = np.log(np.maximum(np.abs(values), np.finfo(np.float64).tiny))
    return np.asarray(
        np.sum(log_magnitudes[:, a_bins], axis=1)
        - np.sum(log_magnitudes[:, b_bins], axis=1),
        dtype=np.float64,
    )


def build_stability_map(
    *,
    pool_seed: int,
    pool: Sequence[CarrierGroup],
    errors_by_codec: Mapping[str, Sequence[Sequence[float]]],
) -> StabilityMap:
    """Build a map from per-group calibration errors.

    ``errors_by_codec[codec][group_id]`` contains all clip/frame errors for
    that group. The codec median is computed first; codec medians are then
    averaged with equal weight, exactly matching the frozen P3 contract.
    """

    _nonnegative_integer(pool_seed, "pool_seed")
    if not pool:
        raise ValueError("pool must not be empty")
    if not errors_by_codec:
        raise ValueError("at least one codec is required")
    codec_names = tuple(sorted(str(name) for name in errors_by_codec))
    per_codec: dict[str, list[float]] = {}
    for codec_name in codec_names:
        samples = errors_by_codec[codec_name]
        if len(samples) != len(pool):
            raise ValueError("each codec must provide one sample sequence per group")
        medians: list[float] = []
        for group_samples in samples:
            values = np.asarray(group_samples, dtype=np.float64)
            if values.ndim != 1 or values.size == 0:
                raise ValueError("each group must have non-empty error samples")
            if not np.all(np.isfinite(values)) or np.any(values < 0.0):
                raise ValueError("stability errors must be finite and non-negative")
            medians.append(float(np.median(values)))
        per_codec[codec_name] = medians

    entries_without_rank: list[StabilityMapEntry] = []
    for group_id, group in enumerate(pool):
        a_bins, b_bins = carrier_sides(group)
        codec_errors = {
            codec_name: per_codec[codec_name][group_id]
            for codec_name in codec_names
        }
        instability = float(np.mean(list(codec_errors.values())))
        entries_without_rank.append(
            StabilityMapEntry(
                group_id=group_id,
                seed=_group_seed(pool_seed, group_id),
                a_bins=tuple(int(value) for value in a_bins),
                b_bins=tuple(int(value) for value in b_bins),
                codec_errors=codec_errors,
                combined_instability=instability,
                stability_score=float(1.0 / (1.0 + instability)),
                rank=0,
            )
        )

    ranked = sorted(
        entries_without_rank,
        key=lambda entry: (-entry.stability_score, entry.group_id),
    )
    entries = tuple(
        StabilityMapEntry(
            group_id=entry.group_id,
            seed=entry.seed,
            a_bins=entry.a_bins,
            b_bins=entry.b_bins,
            codec_errors=dict(entry.codec_errors),
            combined_instability=entry.combined_instability,
            stability_score=entry.stability_score,
            rank=rank,
        )
        for rank, entry in enumerate(ranked, start=1)
    )
    return StabilityMap(
        pool_seed=pool_seed,
        entries=entries,
        codec_names=codec_names,
    )


def map_to_dict(stability_map: StabilityMap) -> dict[str, object]:
    """Serialize the complete stability map to JSON-compatible data."""

    return {
        "pool_seed": stability_map.pool_seed,
        "codec_names": list(stability_map.codec_names),
        "formula": stability_map.formula,
        "entries": [
            {
                "group_id": entry.group_id,
                "seed": entry.seed,
                "a_bins": list(entry.a_bins),
                "b_bins": list(entry.b_bins),
                "codec_errors": dict(entry.codec_errors),
                "combined_instability": entry.combined_instability,
                "stability_score": entry.stability_score,
                "rank": entry.rank,
            }
            for entry in stability_map.entries
        ],
    }


def map_from_dict(raw: Mapping[str, object]) -> StabilityMap:
    """Restore a stability map and validate its scalar fields."""

    entries = tuple(
        StabilityMapEntry(
            group_id=int(item["group_id"]),
            seed=int(item["seed"]),
            a_bins=tuple(int(value) for value in item["a_bins"]),
            b_bins=tuple(int(value) for value in item["b_bins"]),
            codec_errors={
                str(name): float(value)
                for name, value in dict(item["codec_errors"]).items()
            },
            combined_instability=float(item["combined_instability"]),
            stability_score=float(item["stability_score"]),
            rank=int(item["rank"]),
        )
        for item in raw["entries"]
    )
    result = StabilityMap(
        pool_seed=int(raw["pool_seed"]),
        entries=entries,
        codec_names=tuple(str(value) for value in raw["codec_names"]),
        formula=str(raw.get("formula", STABILITY_FORMULA)),
    )
    if result.formula != STABILITY_FORMULA:
        raise ValueError("unsupported stability formula")
    return result


def score_transfer_spearman(
    stability_map: StabilityMap,
    *,
    heldout_error_by_group: Mapping[int, float],
) -> tuple[float, float]:
    """Correlate frozen scores with held-out errors using explicit group IDs.

    ``StabilityMap.entries`` is rank-ordered, while held-out diagnostics are
    accumulated by the original ``group_id``.  Sorting the shared group-ID
    key before constructing both vectors prevents rank position from being
    mistaken for a group identifier.  The returned p-value is descriptive
    only; this synthetic diagnostic is not a hypothesis test.
    """

    score_by_group = {
        int(entry.group_id): float(entry.stability_score)
        for entry in stability_map.entries
    }
    if len(score_by_group) != len(stability_map.entries):
        raise ValueError("stability map group_id values must be unique")
    error_by_group = {
        int(group_id): float(error)
        for group_id, error in heldout_error_by_group.items()
    }
    if set(error_by_group) != set(score_by_group):
        raise ValueError("held-out errors must contain exactly one value per group_id")
    if not all(np.isfinite(value) and value >= 0.0 for value in error_by_group.values()):
        raise ValueError("held-out errors must be finite and non-negative")

    group_ids = sorted(score_by_group)
    scores = np.asarray([score_by_group[group_id] for group_id in group_ids])
    errors = np.asarray([error_by_group[group_id] for group_id in group_ids])
    correlation = spearmanr(scores, errors)
    return float(correlation.statistic), float(correlation.pvalue)


def _group_seed(pool_seed: int, group_id: int) -> int:
    return int(
        np.random.SeedSequence([pool_seed, group_id]).generate_state(
            1, dtype=np.uint64
        )[0]
    )


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _nonnegative_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
