# 盲音频水印：课程公开演示版

这是 Course V2 冻结课程演示系统的独立、清洁导出版本，面向本地教学演示
与代码审查。它不是对原研究原型重新完成公开基准测试的声明。

## 包含内容

- 冻结的 REAL_TOP32 codec-aware carrier selection 与公开 map。
- 原始任意 32-bit blind payload API。
- 四身份模式：固定 32-bit codeword，两两最小汉明距离为 21。有效身份信息
  只有 2 bit，身份识别率不能等同于任意 32-bit 消息恢复率。
- 冻结 operating point：strength `1.28`、拒绝阈值 `8`、payload seed `7`。
- 真实 FFmpeg MP3 128 kbps 编解码流程。
- 简洁 Gradio 界面和独立盲检测器进程。
- 自生成测试信号 smoke test；不分发原始数据集音频。

## V3 8-bit 本地集成候选

仓库另外包含冻结的 V3 8-bit Soft-Code 本地集成候选：`strength=1.60`、
`REAL_TOP32`、seed `7`、6 秒单块，检测器保持 blind 并返回 `IDENTIFIED` 或
`UNKNOWN`。它不会替换 Course V2 入口，也不会改写 Course V2 历史结果。

```bash
PYTHONPATH=src:scripts:. python examples/generate_test_audio.py --output /tmp/v3_demo_input.wav
PYTHONPATH=src:scripts:. python scripts/v3_p3_acceptance.py --output-dir /tmp/v3_p3_acceptance
PYTHONPATH=src:scripts:. python gradio_v3_app.py
```

V3 集成目前只支持本地运行，没有部署到 Render。请阅读
[`docs/V3_P3_INTEGRATION.md`](docs/V3_P3_INTEGRATION.md) 和中文验收记录
[`docs/V3_P3_ACCEPTANCE_ZH.md`](docs/V3_P3_ACCEPTANCE_ZH.md)，了解冻结接口、
P2-V 证据边界和试听限制。

## 快速开始

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[gui,dev]'
python examples/generate_test_audio.py --output /tmp/watermark_test_signal.wav
python scripts/demo.py --input /tmp/watermark_test_signal.wav --identity UESTC-003 --codec mp3
python -m app.gui
```

GUI 默认只绑定 `127.0.0.1`，不会创建公开分享链接。MP3 编码/解码需要系统
安装 FFmpeg。CLI 输出目录包含准备后的原音频、水印 WAV、MP3、MP3 解码 WAV
和盲检测 JSON；生成的音频不会提交到 Git。

## 盲检测器约定

`scripts/detect.py` 和 `python -m app.detector_worker` 只接受接收音频以及可选的
公开 map 路径，不接受 expected identity、clean audio、原始 payload、文件名标签
或缓存答案。超过冻结汉明阈值时返回 `UNKNOWN`。

## 证据与边界

历史 Course V2 结果作为 provenance 记录在 [`docs/RESULTS.md`](docs/RESULTS.md)；
本清洁导出不声称重新跑过 48/48 no-attack 或 46/48 MP3 验证矩阵。展示前请先
阅读 [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md)。

冻结的校准/验证记录使用了外部 MUSAN / OpenSLR SLR17 录音。本仓库不分发 MUSAN
原始音频、压缩包或逐录音 source manifest，只发布聚合后的冻结统计结果并保留
数据集引用。OpenSLR 将 SLR17 标为 CC BY 4.0；使用者仍需保留上游署名并遵守
适用的数据来源条款。

## 许可证与数据状态

本 staging 中的项目代码采用 MIT License。NumPy、SciPy、pytest、Gradio、FFmpeg
及其他依赖仍保留各自的许可证；本仓库不将依赖当作自有代码。未包含 MUSAN 或
其他原始音频，冻结统计结果只引用外部数据来源，不授予录音再分发权。
