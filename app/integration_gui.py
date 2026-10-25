"""Local Gradio integration UI for the frozen V3 candidate and Course V2.

The two modes deliberately use separate callbacks and state.  The V3 detector
callback accepts only the independently selected received audio file; the
embedding message is never passed into that callback.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from .audio_io import AudioData, decode_audio_file, prepare_for_demo, write_wav
from .gui import (
    _compress_action as _legacy_compress_action,
    _detect_action as _legacy_detect_action,
    _embed_action as _legacy_embed_action,
)
from .mp3_codec import encode_decode_mp3
from .session_store import SessionHandle, SessionStore
from .v3_api import V3DetectionResult, embed_message
from .v3_pipeline import detect_uploaded_file


V3_MODE = "V3 8-bit Soft-Code"
LEGACY_MODE = "Legacy Course V2"
V3_MESSAGE_MIN = 0
V3_MESSAGE_MAX = 255
_GUI_SESSION_TTL_SECONDS = 3600
_GUI_SESSION_STORE = SessionStore(ttl_seconds=_GUI_SESSION_TTL_SECONDS)


def _coerce_v3_message(value: object) -> int:
    """Validate the integer message accepted by the public V3 API."""

    if isinstance(value, bool):
        raise ValueError("V3 message must be an integer in the range [0, 255]")
    if isinstance(value, int):
        message = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        message = int(value)
    else:
        raise ValueError("V3 message must be an integer in the range [0, 255]")
    if not V3_MESSAGE_MIN <= message <= V3_MESSAGE_MAX:
        raise ValueError("V3 message must be an integer in the range [0, 255]")
    return message


def _state_payload(state: str | None) -> SessionHandle:
    if not state:
        raise ValueError("请先完成 V3 水印嵌入。")
    try:
        payload = json.loads(state)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("V3 会话状态无效，请重新嵌入。") from error
    if not isinstance(payload, dict):
        raise ValueError("V3 会话状态无效，请重新嵌入。")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        raise ValueError("V3 会话状态缺少有效会话，请重新嵌入。")
    try:
        return _GUI_SESSION_STORE.open(session_id)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise ValueError("V3 会话已失效，请重新嵌入。") from error


def _embed_v3_action(input_path: str | None, message: object):
    """Embed a V3 message and return listenable artifacts plus private GUI state."""

    if not input_path:
        return None, None, None, "请选择本地 WAV/音频文件。"
    session: SessionHandle | None = None
    try:
        value = _coerce_v3_message(message)
        source = prepare_for_demo(decode_audio_file(input_path), duration_seconds=6)
        embedded = embed_message(source, value)
        session = _GUI_SESSION_STORE.create()
        original_path = write_wav(session.path("original_prepared.wav"), source)
        marked_path = write_wav(session.path("watermarked.wav"), embedded.audio)
        state = json.dumps(
            {"session_id": session.root.name},
            ensure_ascii=False,
        )
        info = (
            f"V3 已嵌入消息 {value}。固定协议：6 s / {embedded.sample_rate} Hz；"
            "检测器仍只读取接收音频。"
        )
        return str(original_path), str(marked_path), state, info
    except Exception as error:
        if session is not None:
            session.cleanup()
        return None, None, None, f"V3 嵌入失败：{error}"


def _compress_v3_action(state: str | None):
    """Run real FFmpeg MP3 128 kbps encoding for the current V3 artifact."""

    session: SessionHandle | None = None
    try:
        session = _state_payload(state)
        marked_path = session.path("watermarked.wav")
        if not marked_path.is_file():
            raise FileNotFoundError("V3 嵌入产物已失效，请重新嵌入。")
        marked = decode_audio_file(marked_path)
        mp3_path, decoded_path, _ = encode_decode_mp3(marked, session.root)
        expected_mp3 = session.path("compressed_128k.mp3")
        expected_decoded = session.path("compressed_128k_decoded.wav")
        if (
            Path(mp3_path).resolve(strict=False) != expected_mp3
            or Path(decoded_path).resolve(strict=False) != expected_decoded
            or not expected_mp3.is_file()
            or not expected_decoded.is_file()
        ):
            raise RuntimeError("V3 MP3 产物路径未通过会话范围校验。")
        next_state = json.dumps({"session_id": session.root.name}, ensure_ascii=False)
        return (
            str(expected_mp3),
            str(expected_decoded),
            str(expected_mp3),
            next_state,
            "已完成真实 FFmpeg MP3 128 kbps 编码并解码。可直接检测，或重新上传其他接收音频。",
        )
    except Exception as error:
        if session is not None:
            session.cleanup()
        return None, None, None, None, f"V3 MP3 失败：{error}"


def _format_v3_detection(result: V3DetectionResult, elapsed_seconds: float) -> str:
    """Format blind V3 output without comparing against an expected message."""

    if result.status == "IDENTIFIED" and result.message is not None:
        headline = f"DETECTED: {result.message}"
    else:
        headline = "UNKNOWN / NO VALID WATERMARK"
    return "\n".join(
        (
            headline,
            f"score: {result.presence_score:.6f} / threshold: {result.threshold:.6f}",
            f"margin: {result.margin:.6f}",
            f"duration: {result.duration_seconds:.3f} s",
            f"sample rate: {result.sample_rate} Hz",
            f"detection time: {elapsed_seconds:.3f} s",
        )
    )


def detect_v3_uploaded_file(received_path: str | None) -> str:
    """Blindly detect one independently uploaded received file.

    This callback intentionally has exactly one input: the received file.  It
    does not accept or inspect the embedding message, clean audio, filename,
    identity label, or GUI embedding state.
    """

    if not received_path:
        return "UNKNOWN / NO VALID WATERMARK\n请上传待检测的接收音频。"
    started = time.perf_counter()
    try:
        result = detect_uploaded_file(received_path)
        return _format_v3_detection(result, time.perf_counter() - started)
    except Exception as error:
        return f"DETECTOR ERROR: {error}"


def _toggle_mode(mode: str):
    """Return visibility updates for the two explicitly separated modes."""

    try:
        import gradio as gr
    except ModuleNotFoundError as error:  # pragma: no cover - build-time guard
        raise RuntimeError("GUI dependencies are missing; install requirements.txt") from error
    if mode == V3_MODE:
        return gr.update(visible=True), gr.update(visible=False)
    if mode == LEGACY_MODE:
        return gr.update(visible=False), gr.update(visible=True)
    raise ValueError(f"unknown integration mode: {mode}")


def build_integration_demo() -> Any:
    """Construct the V3/Legacy integration Blocks without launching it."""

    try:
        import gradio as gr
    except ModuleNotFoundError as error:
        raise RuntimeError("GUI dependencies are missing; install requirements.txt") from error

    with gr.Blocks(title="Blind Audio Watermarking Integration Demo") as demo:
        gr.Markdown(
            "# Blind Audio Watermarking\n"
            "本地课程展示入口：V3 8-bit Soft-Code 与 Legacy Course V2 分离运行。"
        )

        with gr.Row():
            mode = gr.Radio(
                [V3_MODE, LEGACY_MODE],
                value=V3_MODE,
                label="Mode / 模式",
            )
            input_audio = gr.Audio(
                label="1. Input audio / 上传音频",
                sources=["upload"],
                type="filepath",
            )

        with gr.Column(visible=True) as v3_section:
            gr.Markdown(
                "## V3 8-bit Soft-Code\n"
                "冻结验证协议：6 秒、48 kHz、消息整数 0–255。"
            )
            v3_message = gr.Number(
                label="V3 message (0–255)", value=173, precision=0
            )
            v3_embed_button = gr.Button("2. Embed V3 watermark", variant="primary")
            v3_embed_info = gr.Textbox(label="V3 embedding status", interactive=False)
            with gr.Row():
                v3_original_audio = gr.Audio(
                    label="Original / prepared audio", type="filepath"
                )
                v3_marked_audio = gr.Audio(
                    label="Watermarked V3 audio", type="filepath"
                )
            v3_embed_state = gr.State()

            gr.Markdown("### Real MP3 128 kbps")
            v3_compress_button = gr.Button("3. Encode real MP3 128 kbps")
            v3_compress_info = gr.Textbox(
                label="V3 compression status", interactive=False
            )
            with gr.Row():
                v3_mp3_audio = gr.Audio(label="Compressed MP3", type="filepath")
                v3_decoded_audio = gr.Audio(
                    label="Decoded MP3 audio", type="filepath"
                )
            v3_received_state = gr.State()

            gr.Markdown(
                "### Independent blind detection\n"
                "重新上传任意接收音频；检测器不读取上方消息或嵌入状态。"
            )
            v3_received_audio = gr.File(
                label="Received audio for blind detection",
                file_types=["audio"],
                type="filepath",
            )
            v3_detect_button = gr.Button("4. Blind detect V3", variant="primary")
            v3_detection_output = gr.Textbox(
                label="V3 detection result", lines=7, interactive=False
            )

            v3_embed_button.click(
                _embed_v3_action,
                inputs=[input_audio, v3_message],
                outputs=[
                    v3_original_audio,
                    v3_marked_audio,
                    v3_embed_state,
                    v3_embed_info,
                ],
            )
            v3_compress_button.click(
                _compress_v3_action,
                inputs=[v3_embed_state],
                outputs=[
                    v3_mp3_audio,
                    v3_decoded_audio,
                    v3_received_audio,
                    v3_received_state,
                    v3_compress_info,
                ],
            )
            v3_detect_button.click(
                detect_v3_uploaded_file,
                inputs=[v3_received_audio],
                outputs=[v3_detection_output],
            )

        with gr.Column(visible=False) as legacy_section:
            gr.Markdown(
                "## Legacy Course V2\n"
                "保留既有身份水印流程与 6 / 15 / 30 秒控制；不调用 V3 参数。"
            )
            with gr.Row():
                legacy_identity = gr.Dropdown(
                    [
                        "NO WATERMARK",
                        "UESTC-001",
                        "UESTC-002",
                        "UESTC-003",
                        "UESTC-004",
                    ],
                    value="UESTC-001",
                    label="Legacy identity",
                )
                legacy_duration = gr.Dropdown(
                    ["6 seconds", "15 seconds", "30 seconds"],
                    value="6 seconds",
                    label="Legacy prepared duration",
                )
            legacy_embed_button = gr.Button("Embed Legacy Course V2 watermark")
            legacy_embed_info = gr.Textbox(
                label="Legacy embedding status", interactive=False
            )
            with gr.Row():
                legacy_original_audio = gr.Audio(
                    label="Legacy original / prepared", type="filepath"
                )
                legacy_marked_audio = gr.Audio(
                    label="Legacy watermarked", type="filepath"
                )
            legacy_embed_state = gr.State()
            legacy_compress_button = gr.Button("Encode Legacy real MP3 128 kbps")
            legacy_compress_info = gr.Textbox(
                label="Legacy compression status", interactive=False
            )
            with gr.Row():
                legacy_mp3_audio = gr.Audio(label="Legacy compressed MP3", type="filepath")
                legacy_decoded_audio = gr.Audio(
                    label="Legacy decoded MP3 audio", type="filepath"
                )
            legacy_received_state = gr.State()
            legacy_detect_button = gr.Button("Blind detect Legacy Course V2")
            legacy_detection_output = gr.Textbox(
                label="Legacy detection result", lines=6, interactive=False
            )

            legacy_embed_button.click(
                _legacy_embed_action,
                inputs=[input_audio, legacy_identity, legacy_duration],
                outputs=[
                    legacy_original_audio,
                    legacy_marked_audio,
                    legacy_embed_state,
                    legacy_received_state,
                    legacy_embed_info,
                ],
            )
            legacy_compress_button.click(
                _legacy_compress_action,
                inputs=[legacy_embed_state],
                outputs=[
                    legacy_mp3_audio,
                    legacy_decoded_audio,
                    legacy_received_state,
                    legacy_compress_info,
                ],
            )
            legacy_detect_button.click(
                _legacy_detect_action,
                inputs=[legacy_received_state],
                outputs=[legacy_detection_output],
            )

        mode.change(
            _toggle_mode,
            inputs=[mode],
            outputs=[v3_section, legacy_section],
        )

        gr.Markdown(
            "本入口仅绑定 localhost。V3 检测结果来自接收音频与公开配置；"
            "正式感知质量门禁仍未建立。"
        )
    return demo
