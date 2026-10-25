# V3 P3 本地集成验收记录

本文件记录冻结的 V3 8-bit Soft-Code 候选如何接入本地演示。它不修改
Course V2、B1/QIM 核心、REAL_TOP32 map、历史实验结果或公开部署。

## 冻结配置

配置来自 V3-P2-V 的 source-disjoint 独立验证；没有根据本轮 P3 smoke
重新选择参数：

- 有效消息：8 bit，整数 `0..255`；物理载荷：32 bit；
- `strength = 1.60`；`presence_threshold = 0.7855073980199624`；
- `selector = REAL_TOP32`；`watermark_seed = 7`；
- 48 kHz、mono、6 秒 V3 block，短输入采用零填充；
- MP3 检查：真实 FFmpeg `libmp3lame`，128 kbps；
- 哈希完整冻结记录：`configs/v3_8bit_candidate_freeze.json`。

Course V2 的 `strength = 1.28`、拒绝阈值 `8` 仍然保留。冻结记录中
selector provenance 内的旧字段属于历史 metadata，不是 V3 配置。

## API 与盲检测

```python
from app.v3_api import embed_message, detect_message

marked = embed_message(clean_audio, 173)
result = detect_message(marked.audio)
```

`embed_message(audio, message)` 接受 `0..255` 的整数。检测 API
`detect_message(audio)` 只读取接收音频以及冻结的公开配置和预共享 selector；
不接收 expected message、clean audio、原始 payload、文件名答案或嵌入阶段缓存。
返回 `IDENTIFIED` 和消息，或 `UNKNOWN` 且消息为 `None`。

本地 demo 将输入转换为 48 kHz mono，V3 只验证 6 秒单块。超过 30 秒或
64 MiB 输入上限的文件应被拒绝。这些是本地演示限制，不是生产服务安全承诺。

## 运行命令

```bash
PYTHONPATH=src:scripts:. python examples/generate_test_audio.py \
  --output /tmp/v3_demo_input.wav
PYTHONPATH=src:scripts:. python scripts/v3_demo.py \
  --input /tmp/v3_demo_input.wav --message 173 --codec mp3 \
  --output-dir /tmp/v3_demo_run
PYTHONPATH=src:scripts:. python scripts/v3_demo.py \
  --detect-input /tmp/v3_demo_run/compressed_128k_decoded.wav
PYTHONPATH=src:scripts:. python scripts/v3_p3_acceptance.py \
  --output-dir /tmp/v3_p3_acceptance
PYTHONPATH=src:scripts:. python scripts/v3_p3_listening_pack.py \
  --input /tmp/v3_demo_input.wav --output-dir /tmp/v3_p3_listening
PYTHONPATH=src:scripts:. python gradio_v3_app.py
```

验收脚本的输出目录只写 JSON metadata/results；smoke 生成的音频位于临时目录。
试听包会把原始准备 WAV、水印 WAV、MP3、MP3 解码 WAV 和中文清单写入显式
指定目录，必须保持在 Git 仓库之外。

真实 FFmpeg 是验收的硬性前提：如果 FFmpeg 不可用，报告必须记录
`mp3_roundtrip = BLOCKED`、整体 `status = BLOCKED` 和阻塞项
`FFMPEG_UNAVAILABLE`，不能返回整体 PASS。错误 key 的 gate 也采用严格规则：
只有检测结果为 `UNKNOWN` 且 `message = None` 时才算通过。CLI 备用流程有 120 秒
超时；未预期的验收异常会写入结构化 JSON 报告。

## GUI 模式边界

集成 GUI 明确区分两种模式：

1. **V3 8-bit Soft-Code**：冻结的 6 秒 V3 API、独立盲检测和真实 MP3 128 kbps；
2. **Legacy Course V2**：原有 Course V2 身份/载荷流程及历史 6/15/30 秒控制。

V3 是额外的本地集成入口，不替换现有 Course V2 入口，也不改写其历史指标。
GUI 默认只绑定 localhost，`share=False`。

## 证据与统计边界

V3-P2-V 独立验证中的真实 MP3 128 kbps 结果为：

| 候选 | 正确接受 trial | 正确接受 source |
| --- | ---: | ---: |
| 8-bit Soft-Code | 117/120 | 58/60 |
| 12-bit Soft-Code | 97/120 | 45/60 |

这两组数字是先前 source-disjoint 独立验证证据，不是本轮 P3 smoke 新产生的
benchmark。P3 验收只检查四条固定消息 `0/1/173/255`、无水印 UNKNOWN、错误
key probe、非法输入、大小/时长保护、会话清理、CLI 备用流程和一次真实 FFmpeg
MP3 往返。

P2-V 负例数量有限：8-bit clean FPR 为 `0/60`，clean-MP3 FPR 为 `1/60`，
wrong-key MP3 acceptance 为 `0/120`。这些有限样本不能证明总体 FPR 小于 1%。
检测器只能根据接收音频和冻结公开配置作判决；拒绝时必须显示 `UNKNOWN`，不能
使用缓存答案。

正式 V3 证据只覆盖 6 秒单块。Course V2 的 15/30 秒模式仍是历史/legacy
功能，不能写成 V3 已验证的多块结果。MP3 范围限定为本地真实 FFmpeg
`libmp3lame` 128 kbps 编解码。

`FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`。试听包只是 preliminary
listening screening，不是正式听感实验，也不能证明水印不可感知。

## 部署限制

本阶段不部署 Render、不替换公开网页、不创建云端上传服务、不生成 public share
URL。没有授权的容器或生产资源测试时，验收报告应记录：

`RENDER_FEASIBILITY = LOCAL_PROXY_ONLY`

未来部署必须另行完成资源、隐私、浏览器、临时文件和多用户安全审查。

## Task 7 初次本地核验（系统默认环境，2026-10-25）

本节只记录最终核验，不改变冻结配置、算法源码或历史实验结果。

- 当前分支：`feat/v3-8bit-integration`；核验前 HEAD：`f0a3dc6`。
- `compileall`：PASS。
- 全量 `pytest -q -p no:cacheprovider`：`100 passed, 1 skipped`；唯一跳过项是
  `tests/test_integration_gui.py`，原因是当前环境没有安装 `gradio`。
- `git diff --check`：PASS；冻结核心和历史结果路径 diff audit：PASS；Git 跟踪的
  音频/模型文件扫描：PASS（未发现匹配文件）。
- acceptance script：PASS。四条固定消息 `0/1/173/255` 均识别成功；真实 FFmpeg
  `libmp3lame` 128 kbps 往返成功；clean audio 为 `UNKNOWN`；wrong-key 为
  `UNKNOWN` 且 `message = None`；输入大小/时长限制、非法输入和 session cleanup
  均通过。最终复核峰值 RSS 约 `133.059 MB`。
- 独立 CLI smoke：PASS。消息 `173` 经 MP3 编解码后由 blind detector 返回
  `IDENTIFIED`；单独上传 clean WAV 返回 `UNKNOWN`。
- GUI/browser：在系统默认环境中 BLOCKED。执行
  `GRADIO_ANALYTICS_ENABLED=False PYTHONPATH=src:scripts:. python gradio_v3_app.py`
  时因 `ModuleNotFoundError: No module named 'gradio'` 退出，因此没有声称 Blocks
  构造、localhost HTTP 或浏览器交互通过。未安装依赖；CLI fallback 保留可用。
- `FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`；`RENDER_FEASIBILITY = LOCAL_PROXY_ONLY`。

因此该次系统默认环境核验中，本地 API、MP3、盲检测、拒绝和 CLI 集成门禁通过，
但 GUI/browser 门禁受环境依赖阻塞。后续隔离运行时复核见下节；本记录不得表述为
已完成线上部署或正式感知质量验证。

## b99846d 后的 Gradio 隔离运行时复核

本节记录 transport 修复后的新鲜本地证据。它只更新验收文档，不改变冻结算法、
Course V2、历史实验或公开部署配置。

### 隔离环境

- 环境目录：`/tmp/v3-p3-gradio-venv2`；Python `3.13.5`；不属于仓库，未提交。
- `requirements.txt` 保持 pinned；实际环境版本：Gradio `4.44.1`、
  `gradio_client = 1.3.0`、`audioop-lts = 0.2.2`。
- 可复现的隔离安装命令：

  ```bash
  /home/nsk/anaconda3/bin/python -m venv /tmp/v3-p3-gradio-venv2
  /tmp/v3-p3-gradio-venv2/bin/python -m pip install \
    -r /home/nsk/blind-audio-watermarking-v3-p0/requirements.txt
  ```

  依赖仅安装在 `/tmp/v3-p3-gradio-venv2`；没有写入仓库，也没有修改系统级
  Python 环境。

### Server 与 Gradio-client

- 本地服务启动：PASS；绑定 `127.0.0.1:7863`，`share=False`。
- `GET /`：HTTP `200`。
- `GET /config`：HTTP `200`；配置版本 `4.44.1`。
- Gradio-client callback smoke：PASS，使用确定性的 harmonic fixture：
  - V3 message `173` embed：PASS；
  - 真实 FFmpeg MP3 `128 kbps`：PASS；
  - received output：MP3 `File`；
  - blind detect：`DETECTED: 173`；
  - clean received WAV：`UNKNOWN`；
  - V3 / Legacy toggle callbacks：均无异常返回。

### Transport 修复说明

第一次使用 `gr.Audio(type="filepath", format="wav")` 作为接收输入时，Gradio
会通过 `audio_from_file/audio_to_file` 处理 FileData，并将 float32 WAV 量化为
int16，导致 MP3 解码输出到盲检测器前丢失冻结 V3 信号。提交 `b99846d`
只修复 GUI transport：

- `v3_received_audio` 改为
  `gr.File(file_types=["audio"], type="filepath")`，保留上传文件字节；
- 压缩回调把 MP3 文件路径传给 received File；
- decoded WAV 仍作为独立 playback 音频输出；
- detector 仍只接收 received-file path，不接收 expected message、clean audio
  或 embedding state。

### 浏览器边界与最终状态

当前 in-app browser backend 不可用：`browsers.list()` 返回空列表。因此没有
浏览器级点击、上传和播放证据；浏览器状态记为
`BROWSER_INTERACTION = NOT_ESTABLISHED / UNAVAILABLE`，不能写成 PASS。

```ini
GRADIO_SERVER = PASS
GRADIO_CLIENT_SMOKE = PASS
BROWSER_INTERACTION = NOT_ESTABLISHED / UNAVAILABLE
V3_P3_STATUS = PARTIAL
PUBLIC_INTEGRATION_READINESS = CONDITIONAL
FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED
RENDER_FEASIBILITY = LOCAL_PROXY_ONLY
```

因此 server/client transport 和盲检测流程已有真实本地证据，但浏览器级验收及
正式感知质量门禁仍未建立。
