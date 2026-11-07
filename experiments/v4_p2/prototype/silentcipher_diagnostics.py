"""Faithful, read-only trace of SilentCipher's official message decoder stages."""
from __future__ import annotations
import numpy as np
from scipy import stats
import torch


def parse_frame_predictions(frame_predictions: np.ndarray, message_len: int = 21) -> dict:
    pred = np.asarray(frame_predictions, dtype=np.int64)
    trimmed = pred[: (len(pred) // message_len) * message_len]
    if trimmed.size == 0:
        return {"stage": "FRAME_TRIM", "frame_count": int(pred.size), "group_count": 0}
    grouped = trimmed.reshape(-1, message_len)
    modal = np.asarray(stats.mode(grouped, axis=0, keepdims=False).mode, dtype=np.int64)
    hits = np.flatnonzero(modal == 0)
    confidence = float(np.mean(grouped == modal[None, :]))
    info = {"stage": "MODE", "frame_count": int(pred.size), "group_count": int(grouped.shape[0]),
            "modal_symbols": modal.tolist(), "confidence": confidence,
            "frame_symbol_histogram": {str(int(k)): int(v) for k, v in zip(*np.unique(pred, return_counts=True))}}
    if not hits.size:
        info.update({"stage": "TERMINATOR", "terminator_index": None, "parse_error": "MISSING_TERMINATOR"})
        return info
    end = int(hits.min())
    symbols = modal[:message_len-1] if end == message_len else np.concatenate((modal[end+1:], modal[:end]))
    shifted = symbols - 1
    if np.any(shifted < 0) or np.any(shifted > 3):
        info.update({"stage": "SYMBOL_RANGE", "terminator_index": end, "parse_error": "SYMBOL_OUT_OF_RANGE"})
        return info
    bitstr = "".join(f"{int(x):02b}" for x in shifted)
    decoded = [int(bitstr[i:i+8], 2) for i in range(0, len(bitstr) - 7, 8)]
    info.update({"stage": "MESSAGE", "terminator_index": end, "symbols": shifted.tolist(), "candidate": decoded})
    return info


def trace_official_decoder(model, audio: np.ndarray, sample_rate: int = 44100) -> dict:
    """Re-run preprocessing/inference/official parser stages without changing upstream code."""
    y = np.asarray(audio, dtype=np.float32)
    if y.ndim == 2:
        if y.shape[1] != 1:
            raise ValueError("trace expects mono input")
        y = y[:, 0]
    if sample_rate != model.sr:
        import librosa
        y = librosa.resample(y, orig_sr=sample_rate, target_sr=model.sr)
    power = float(np.mean(y ** 2))
    if power <= 0 or not np.isfinite(power):
        return {"stage": "NORMALIZATION", "parse_error": "ZERO_OR_INVALID_POWER"}
    normalized = y * np.sqrt(model.average_energy_VCTK / power)
    tensor = torch.as_tensor(normalized, dtype=torch.float32, device=model.device)[None, None]
    with torch.no_grad():
        carrier, _ = model.stft.transform(tensor.squeeze(1))
        carrier = carrier[:, None]
        outputs = []
        for decoder_index, decoder in enumerate(model.dec_m):
            logits = decoder(carrier)
            frame_pred = torch.argmax(logits[0, 0], dim=0).detach().cpu().numpy().reshape(-1)
            result = parse_frame_predictions(frame_pred, model.config.message_len)
            result.update({"decoder_index": decoder_index, "frame_predictions": frame_pred.tolist(), "logits_shape": list(logits.shape),
                           "logits_min": float(logits.min().item()), "logits_max": float(logits.max().item()),
                           "logits_mean": float(logits.mean().item()), "predicted_frame_count": int(frame_pred.size)})
            outputs.append(result)
    return {"status": "TRACE_OK", "per_decoder": outputs}
