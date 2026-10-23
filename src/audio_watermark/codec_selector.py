"""Frozen deterministic B1 carrier selection from a P3 stability map."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

import numpy as np

from .carrier import CarrierGroup
from .codec_stability import StabilityMap


@dataclass(frozen=True)
class CodecAwareCarrierSelector:
    """Select one of the frozen top-k map groups from public frame metadata."""

    selected_groups: tuple[CarrierGroup, ...]
    selected_group_ids: tuple[int, ...]
    top_k: int
    watermark_seed: int
    map_sha256: str

    @classmethod
    def from_stability_map(
        cls,
        stability_map: StabilityMap,
        *,
        top_k: int,
        watermark_seed: int,
    ) -> "CodecAwareCarrierSelector":
        if isinstance(top_k, bool) or not isinstance(top_k, Integral) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        if top_k > len(stability_map.entries):
            raise ValueError("top_k must not exceed the stability map size")
        if isinstance(watermark_seed, bool) or not isinstance(watermark_seed, Integral) or watermark_seed < 0:
            raise ValueError("watermark_seed must be a non-negative integer")

        entries = tuple(stability_map.entries[: int(top_k)])
        groups = tuple(
            CarrierGroup(
                bins=entry.a_bins + entry.b_bins,
                signs=(1,) * len(entry.a_bins) + (-1,) * len(entry.b_bins),
            )
            for entry in entries
        )
        return cls(
            selected_groups=groups,
            selected_group_ids=tuple(entry.group_id for entry in entries),
            top_k=int(top_k),
            watermark_seed=int(watermark_seed),
            map_sha256=stability_map.sha256,
        )

    def group_for_frame(self, frame_index: int) -> CarrierGroup:
        """Return the deterministic public group assigned to one frame."""

        if isinstance(frame_index, bool) or not isinstance(frame_index, Integral) or frame_index < 0:
            raise ValueError("frame_index must be a non-negative integer")
        state = np.random.SeedSequence(
            [self.watermark_seed, int(frame_index)]
        ).generate_state(1, dtype=np.uint64)
        return self.selected_groups[int(state[0] % self.top_k)]


@dataclass(frozen=True)
class FrozenSubsetCarrierSelector:
    """Select one group from a frozen, rank-ordered subset.

    P3C uses this selector for TOP32, BOTTOM32, and pre-registered random
    subsets. The frame assignment is identical for every subset; only the
    selected group IDs differ.
    """

    selected_groups: tuple[CarrierGroup, ...]
    selected_group_ids: tuple[int, ...]
    subset_size: int
    watermark_seed: int
    map_sha256: str

    @classmethod
    def from_stability_map(
        cls,
        stability_map: StabilityMap,
        *,
        group_ids: tuple[int, ...],
        watermark_seed: int,
    ) -> "FrozenSubsetCarrierSelector":
        if not group_ids:
            raise ValueError("group_ids must not be empty")
        if len(set(group_ids)) != len(group_ids):
            raise ValueError("group_ids must be unique")
        if (
            isinstance(watermark_seed, bool)
            or not isinstance(watermark_seed, Integral)
            or watermark_seed < 0
        ):
            raise ValueError("watermark_seed must be a non-negative integer")

        requested = {int(group_id) for group_id in group_ids}
        entries_by_id = {entry.group_id: entry for entry in stability_map.entries}
        if not requested.issubset(entries_by_id):
            raise ValueError("group_ids must come from the frozen stability map")
        entries = tuple(
            entry for entry in stability_map.entries if entry.group_id in requested
        )
        if len(entries) != len(requested):
            raise ValueError("stability map group_id values must be unique")
        groups = tuple(
            CarrierGroup(
                bins=entry.a_bins + entry.b_bins,
                signs=(1,) * len(entry.a_bins) + (-1,) * len(entry.b_bins),
            )
            for entry in entries
        )
        return cls(
            selected_groups=groups,
            selected_group_ids=tuple(entry.group_id for entry in entries),
            subset_size=len(entries),
            watermark_seed=int(watermark_seed),
            map_sha256=stability_map.sha256,
        )

    def group_for_frame(self, frame_index: int) -> CarrierGroup:
        """Return the public subset group assigned to one frame."""

        if (
            isinstance(frame_index, bool)
            or not isinstance(frame_index, Integral)
            or frame_index < 0
        ):
            raise ValueError("frame_index must be a non-negative integer")
        state = np.random.SeedSequence(
            [self.watermark_seed, int(frame_index)]
        ).generate_state(1, dtype=np.uint64)
        return self.selected_groups[int(state[0] % self.subset_size)]
