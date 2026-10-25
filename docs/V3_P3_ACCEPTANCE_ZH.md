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
