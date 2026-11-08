"""Experimental SilentCipher score decoders; official model/source are untouched."""
from __future__ import annotations

import numpy as np


def _group_scores(frame_scores: np.ndarray, message_len: int) -> np.ndarray:
    scores = np.asarray(frame_scores, dtype=np.float32)
    if scores.ndim != 2 or scores.shape[1] != 5:
        raise ValueError("frame_scores must have shape [frames, 5]")
    n_groups = scores.shape[0] // message_len
    if n_groups < 1:
        raise ValueError("not enough frames for one message block")
    return scores[:n_groups * message_len].reshape(n_groups, message_len, 5)


def _hard_mode(groups: np.ndarray) -> np.ndarray:
    hard = np.argmax(groups, axis=2)
    # np.argmax chooses the lowest symbol on ties, matching scipy.stats.mode.
    return np.argmax(np.stack([(hard == k).sum(axis=0) for k in range(5)]), axis=0)


def _parse_symbols(symbols: np.ndarray, message_len: int) -> tuple[str | None, int | None, str | None]:
    terminators = np.flatnonzero(symbols == 0)
    if not terminators.size:
        return None, None, "MISSING_TERMINATOR"
    end = int(terminators[0])
    payload = symbols[:message_len - 1] if end == message_len - 1 else np.concatenate((symbols[end + 1:], symbols[:end]))
    if payload.size != message_len - 1 or np.any((payload < 1) | (payload > 4)):
        return None, end, "INVALID_PAYLOAD_SYMBOLS"
    bit_text = "".join(f"{int(v - 1):02b}" for v in payload)
    if len(bit_text) != 40:
        return None, end, "INVALID_MESSAGE_LENGTH"
    message = bytes(int(bit_text[i:i + 8], 2) for i in range(0, 40, 8))
    return message.hex().upper(), end, None


def _decode(frame_scores: np.ndarray, message_len: int, soft: bool) -> dict:
    groups = _group_scores(frame_scores, message_len)
    frame_symbols = np.argmax(groups, axis=2)
    if soft:
        aggregate = groups.mean(axis=0)
        symbols = np.argmax(aggregate, axis=1)
        # Match the official confidence meaning: fraction of frame symbols
        # agreeing with the chosen repeated-message symbol at each position.
        confidence = float(np.mean(frame_symbols == symbols[None, :]))
        selected_mean_score = float(np.mean(np.max(aggregate, axis=1)))
    else:
        symbols = _hard_mode(groups)
        confidence = float(np.mean(frame_symbols == symbols[None, :]))
        selected_mean_score = None
    candidate, end, error = _parse_symbols(symbols, message_len)
    return {
        "method": "soft_temporal_mean" if soft else "official_hard_argmax_mode",
        "candidate": candidate,
        "confidence": confidence,
        "terminator_index": end,
        "parse_error": error,
        "group_count": int(groups.shape[0]),
        "frame_count": int(groups.shape[0] * message_len),
        "symbols": symbols.astype(int).tolist(),
        "selected_mean_score": selected_mean_score,
    }


def decode_official_scores(frame_scores: np.ndarray, message_len: int = 21) -> dict:
    """Reproduce official argmax -> temporal mode -> terminator parse semantics."""
    return _decode(frame_scores, message_len, soft=False)


def decode_soft_scores(frame_scores: np.ndarray, message_len: int = 21) -> dict:
    """Average per-class frame scores at repeated symbol positions before argmax."""
    return _decode(frame_scores, message_len, soft=True)
