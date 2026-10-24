"""Pure protocol helpers shared by the bounded V3-P2 development scripts."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np


def message_for_seed(seed: int, payload_bits: int) -> tuple[int, ...]:
    """Generate the predeclared deterministic binary message for one capacity."""

    if int(payload_bits) <= 0:
        raise ValueError("payload_bits must be positive")
    generator = np.random.default_rng(int(seed))
    return tuple(int(value) for value in generator.integers(0, 2, size=int(payload_bits)))


def assign_development_roles(
    records: Iterable[dict[str, object]], *, calibration_count: int = 5
) -> list[dict[str, object]]:
    """Assign category-balanced calibration/pilot roles without using P1 test rows."""

    if calibration_count != 5:
        raise ValueError("the frozen P2 protocol requires five calibration sources per category")
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if str(record.get("split")) != "dev":
            continue
        grouped[str(record["category"])].append(dict(record))
    if not grouped or any(len(rows) != 2 * calibration_count for rows in grouped.values()):
        raise ValueError("P2 requires ten development sources per category")
    result: list[dict[str, object]] = []
    for category in sorted(grouped):
        rows = sorted(grouped[category], key=lambda row: str(row["record_id"]))
        for index, row in enumerate(rows):
            row["p2_role"] = "calibration" if index < calibration_count else "pilot"
            result.append(row)
    return result
