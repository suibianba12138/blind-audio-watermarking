"""Minimal localhost-only SilentCipher Gradio application."""
from __future__ import annotations
import atexit
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio_io import decode_audio_file, resample_audio, AudioData
from .silentcipher_adapter import SilentCipherAdapter
from .v4_tempfiles import ArtifactStore

TARGET_SR = 44100
TARGET_SECONDS = 12
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
_STORE = ArtifactStore(os.environ.get("V4_P2_TMP_ROOT") or None, ttl_seconds=3600)
_ADAPTER = SilentCipherAdapter(cpu_threads=int(os.environ.get("V4_P2_CPU_THREADS", "4")))
atexit.register(_STORE.cleanup)


def _prepare_path(path: str) -> np.ndarray:
    p = Path(path)
    if not p.is_file() or p.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("请上传有效且小于 16 MiB 的音频文件。")
    audio = decode_audio_file(p)
    mono = resample_audio(audio, TARGET_SR).samples.astype(np.float32)
    count = TARGET_SR * TARGET_SECONDS
    if len(mono) >= count:
        mono = mono[:count]
    else:
        mono = np.pad(mono, (0, count - len(mono)))
    return mono


def _parse_message(text: str) -> tuple[int, ...]:
    compact = "".join((text or "").split()).replace("0x", "").replace("0X", "")
    if len(compact) != 10:
        raise ValueError("消息请输入恰好 10 位十六进制字符（5 字节）。")
    try:
        raw = bytes.fromhex(compact)
    except ValueError as exc:
        raise ValueError("消息格式无效，请输入十六进制字符。") from exc
    return tuple(raw)


def embed_callback(input_path: str | None, message_text: str, *, adapter=None, store=None):
    adapter = adapter or _ADAPTER
    store = store or _STORE
    if not input_path:
        return None, None, None, "请先上传音频。"
    job = None
    try:
        message = _parse_message(message_text)
        original = _prepare_path(input_path)
        job = store.new_job()
        marked_result = adapter.embed(original, message, TARGET_SR)
        original_path = store.checked_path(job, "original.wav")
        marked_path = store.checked_path(job, "watermarked.wav")
        sf.write(original_path, original, TARGET_SR, subtype="PCM_16")
        sf.write(marked_path, marked_result["audio"], TARGET_SR, subtype="PCM_16")
        summary = (f"嵌入完成；消息 {bytes(message).hex().upper()}；"
                   f"SNR {marked_result['embedding_snr_db']:.2f} dB；"
                   f"CPU 嵌入 {marked_result['seconds']:.2f} s；"
                   f"模型加载 {marked_result.get('model_load_seconds') or 0:.2f} s。")
        return str(original_path), str(marked_path), str(marked_path), summary
    except ValueError as exc:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, None, str(exc)
    except Exception as exc:
        logging.getLogger(__name__).warning("embed failed category=%s", type(exc).__name__)
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, None, "音频无法解码或嵌入失败，请检查文件格式。"


def compress_callback(marked_path: str | None, *, store=None):
    store = store or _STORE
    job = None
    try:
        if not marked_path:
            return None, None, None, "请先完成嵌入。"
        source = Path(marked_path).resolve()
        if not source.is_file() or source.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValueError("音频文件无效或超过大小限制，请重新上传。")
        job = store.new_job()
        mp3_path = store.checked_path(job, "compressed_128k.mp3")
        wav_path = store.checked_path(job, "compressed_decoded.wav")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                        "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3_path)],
                       check=True, shell=False, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3_path),
                        "-ac", "1", "-ar", str(TARGET_SR), "-c:a", "pcm_f32le", "-f", "wav", str(wav_path)],
                       check=True, shell=False, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return str(mp3_path), str(wav_path), str(mp3_path), str(wav_path), "真实 FFmpeg MP3 128 kbps 往返完成。"
    except ValueError as exc:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, None, str(exc)
    except Exception:
        if job is not None:
            shutil.rmtree(job, ignore_errors=True)
        return None, None, None, None, "MP3 转码失败，请确认 FFmpeg/libmp3lame 可用。"


def detect_callback(received_path: str | None, *, adapter=None):
    adapter = adapter or _ADAPTER
    if not received_path:
        return "请独立上传待检测音频。"
    try:
        received = _prepare_path(received_path)
        result = adapter.detect(received, TARGET_SR)
        candidate = result.get("candidate")
        msg = bytes(candidate).hex().upper() if candidate is not None else "无消息候选"
        score = result.get("confidence")
        score_text = "无" if score is None else f"{score:.6f}"
        return (f"判决：{result['state']}\n消息候选：{msg}\n逐帧一致度：{score_text}\n"
                f"存在性校准：{result.get('presence_calibration', 'PROVISIONAL')}\n"
                f"检测耗时：{result.get('seconds', 0):.2f} s")
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        logging.getLogger(__name__).warning("detect failed category=%s", type(exc).__name__)
        return "音频无法解码或检测失败，请检查文件格式。"


def build_demo():
    import gradio as gr
    with gr.Blocks(title="SilentCipher Local Watermark MVP") as demo:
        gr.Markdown("# SilentCipher 本地盲音频水印\n官方 44.1 kHz 权重 · 12 秒 · 40 bit · CPU 单 worker · presence 阈值为临时校准")
        input_audio = gr.File(label="原始音频（上传）", file_types=["audio"], type="filepath")
        message = gr.Textbox(label="固定 5 字节消息（10 位十六进制）", value="123456789A")
        embed_btn = gr.Button("嵌入水印", variant="primary")
        embed_status = gr.Textbox(label="嵌入结果", interactive=False)
        original_out = gr.Audio(label="准备后的原音", type="filepath")
        marked_out = gr.Audio(label="带水印音频", type="filepath")
        marked_file = gr.File(label="下载带水印 WAV")
        embed_btn.click(embed_callback, [input_audio, message], [original_out, marked_out, marked_file, embed_status], concurrency_limit=1, api_name="embed")
        compress_btn = gr.Button("真实 MP3 128 kbps 往返")
        codec_status = gr.Textbox(label="压缩结果", interactive=False)
        mp3_out = gr.Audio(label="MP3 压缩结果", type="filepath")
        decoded_out = gr.Audio(label="MP3 解码音频", type="filepath")
        mp3_file = gr.File(label="下载 MP3")
        decoded_file = gr.File(label="下载 MP3 解码 WAV")
        compress_btn.click(compress_callback, [marked_out], [mp3_out, decoded_out, mp3_file, decoded_file, codec_status], concurrency_limit=1, api_name="mp3_roundtrip")
        gr.Markdown("## 独立盲检测\n重新上传接收音频；检测函数不读取嵌入消息、会话状态或文件名。")
        received = gr.File(label="接收音频（独立上传）", file_types=["audio"], type="filepath")
        detect_btn = gr.Button("盲检测", variant="primary")
        detection = gr.Textbox(label="检测详情", lines=5, interactive=False)
        detect_btn.click(detect_callback, [received], [detection], concurrency_limit=1, api_name="detect")
    return demo.queue(default_concurrency_limit=1, max_size=4)


def main():
    demo = build_demo()
    demo.launch(server_name="127.0.0.1", server_port=int(os.environ.get("V4_P2_PORT", "7861")),
                share=False, show_error=False, inbrowser=False)


if __name__ == "__main__":
    main()
