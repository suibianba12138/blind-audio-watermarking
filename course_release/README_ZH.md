# DSP 数字音频水印课程版

本目录整理了冻结的参考辅助 C2/C3 DSP 模式、命令行示例、最小测试、一首已授权的 C3-16 精选音乐案例和简明实验结果。不会包含训练数据、模型权重、Python 环境或完整实验工作区。

## 工作模式

| 模式 | 载荷 | 长音频用法 | 检测信息 |
|---|---:|---|---|
| C2 Robust | 8 bit / 6 秒 | 逐块承载鲁棒消息 | 需要对应的无水印原音参考 |
| C2 Long-ID | 一个 32-bit 身份 | 72 秒内将四个 ID 字节重复三次 | 重复身份，不是 96 bit 独立信息 |
| C3-16 High-Capacity | 16 bit / 6 秒 | 12 个独立块在 72 秒承载 192 bit | 需要对应的无水印原音参考 |

C2 和 C3 都是**参考辅助、非盲检测**。检测器不接收目标消息；它先估计消息，再用独立的存在性阈值判定 `IDENTIFIED` 或 `UNKNOWN`。本代码用于课程演示，不是密码学认证系统。

## 安装与 smoke test

要求 Python 3.10 或更新版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
```

`configs/demo.example.json` 中的公开 demo key 与冻结评估 key 不同。发布版源码要求调用方显式传入 key，因此不会分发冻结 key。Smoke test 使用随包附带的授权音乐片段，不复现 Locked Test 成绩。

## 6 秒嵌入与保存回读检测

```bash
python examples/embed_detect_6s.py \
  --mode c2-8 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7 \
  --key course-demo-public-v1 \
  --output /tmp/c2-marked.wav

python examples/embed_detect_6s.py \
  --mode c3-16 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7C3 \
  --key course-demo-public-v1 \
  --output /tmp/c3-marked.wav
```

示例输出 float32 WAV，关闭文件并重新读取后，再使用原音参考检测。目标消息只在检测完成后用于评分。

## 72 秒载荷布局

`examples/payload_layout.py` 提供两种布局：

- C2 Long-ID 将 32-bit 身份拆成四个字节，并在 12 个 6 秒块中重复三次。
- C3-192 将 192-bit 数据拆成 12 个独立的 16-bit 消息。

`examples/embed_detect_72s.py` 可对 48 kHz、72 秒 WAV 执行嵌入、float32 保存回读及逐块检测，并报告融合消息。此示例不执行编解码，也不宣称公开 demo key 可以复现冻结成绩。

```bash
python examples/embed_detect_72s.py \
  --mode c2-long-id \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message 12345678 \
  --key course-demo-public-v1 \
  --output /tmp/c2-long-id.wav

python examples/embed_detect_72s.py \
  --mode c3-192 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message D42DEE6FA235F3C07531FD862283452DCB56FF6A8F621E41 \
  --key course-demo-public-v1 \
  --output /tmp/c3-192.wav
```

## 真实 FFmpeg 编码

`examples/transcode_ffmpeg.py` 会调用 FFmpeg，将 WAV 实际编码为 128 kbps MP3 或 AAC-LC/M4A；也可将编码文件解码回 float32 WAV：

```bash
python examples/transcode_ffmpeg.py marked.wav marked.mp3 --codec mp3 --decode-to marked_mp3_decoded.wav
python examples/transcode_ffmpeg.py marked.wav marked.m4a --codec aac --decode-to marked_aac_decoded.wav
```

FFmpeg 需单独安装。脚本执行真实编码/解码，不模拟编解码失真。

## 结果与边界

请阅读 `EVIDENCE_SUMMARY.md`，其中分别列出 C2 Locked Test、重复 32-bit Long-ID、C3-16 独立评估和单曲精选案例。精选单曲 12/12 是经过筛选的展示案例，不代表总体可靠率。C3-16 独立评估中的 AAC 错误如实保留。

## 精选音乐

`media/selected_c3_16_showcase/` 含一个获许可的 72 秒 C3-16 案例：原音/水印 WAV、整段 MP3/AAC、192-bit 消息、真实检测图和原始图表 CSV。署名与许可见 `THIRD_PARTY_NOTICES.md`。
