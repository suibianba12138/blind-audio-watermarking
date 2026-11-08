<div align="center">

# Robust Audio Watermarking Studio
## 鲁棒盲音频数字水印系统

**嵌入 · 信道处理 · 盲检测 · 信号分析**

[**V4 项目展示**](https://shengkaini.com/blind-audio-watermarking/) · [**V4 源码与本地 Studio**](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) · [**V3 在线演示**](https://blind-audio-watermarking-demo.onrender.com/) · [**English README**](README.md)

</div>

---

## 项目简介

这是一个数字信号处理课程设计项目，研究如何在音频中嵌入信息，并在经历真实信道处理后，仅凭接收音频恢复水印，而**不向检测器提供原始音频或预期消息**。

项目由 **Course V2 传统身份水印**、**V3 FFT/QIM + Soft-Code 8-bit 水印**，逐步发展为 **V4 Robust Audio Watermarking Studio**。V4 将 Sony Research 第三方预训练 SilentCipher、真实 MP3/AAC 编解码、独立盲检测和时频分析集成在一个本地 Gradio Studio 中；V3 继续作为单独、可复现的传统 DSP 基线。

**当前仓库状态（2026-11-08）：** 默认 `main` 分支仍是 V3/Legacy 稳定代码和现有在线演示；**V4 代码位于 [`upgrade/v4-github-prep`](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) 分支和 [Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5)，尚未合并。** 因此 README 以 V4 为项目展示重点，**不代表 `main` 已经包含 V4 Studio 的可运行源码**。

## 项目入口

| 入口 | 内容 | 状态 |
| --- | --- | --- |
| [V4 项目展示页](https://shengkaini.com/blind-audio-watermarking/) | 40-bit 实验结果、系统架构及历史版本 | 静态展示，**不能在线执行 V4 推理** |
| [V4 分支](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep) | 完整本地 Studio、实验与复现说明 | Draft；运行需要外部模型文件 |
| [V3 在线演示](https://blind-audio-watermarking-demo.onrender.com/) | 传统 DSP/Legacy 真实音频处理 | **仅 V3**，不是 V4 在线服务 |
| [V2/V3 方法](docs/METHOD.md) · [结果](docs/RESULTS.md) | 原有算法、冻结参数与历史证据 | `main` 保留 |
| [V4 实验报告](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep/docs/reports/v4) | 正负实验、边界条件、复现证据 | V4 分支 |

## V2 → V3 → V4

| | Course V2 | V3 传统 DSP | V4 Studio |
| --- | --- | --- | --- |
| **算法/后端** | REAL_TOP32 频谱 QIM | FFT/QIM + Soft-Code | Sony SilentCipher 预训练模型 + 冻结的 V3 基线 |
| **消息** | 四个固定身份；32-bit 冗余码字仅承载 **2 bit 身份信息** | 0–255 可变 8-bit 消息 | 神经水印 40-bit（5 字节），或 V3 8-bit 模式 |
| **典型输入** | 6 秒、单声道 | 6 秒 / 48 kHz 单声道 | 神经：12 秒 / 44.1 kHz；V3：6 秒 / 48 kHz |
| **历史结果** | MP3 身份识别 **46/48** | MP3 正确接受 **117/120** | 见下方 V4 评估 |
| **当前定位** | 历史教学参考 | 算法基线与在线演示 | 主要本地实验系统 |

**务必区分：** V2 身份识别、V3 8-bit 消息恢复和 V4 40-bit 消息恢复采用不同的任务与实验协议，不能简单把百分比直接比较。SilentCipher **不是本项目自行提出或训练的模型**，本项目的工作主要是系统集成、实验协议、信道处理与评估展示。

## V4 Studio 的四个模块

1. **Watermark（水印嵌入）**：上传音频，选择 40-bit 神经水印或 8-bit DSP 水印，试听、下载原音与水印 WAV。
2. **Channel Lab（信道实验）**：通过 **真实 FFmpeg** 完成 MP3 128 kbps、AAC-LC/M4A 128 kbps 编解码，以及加噪、裁剪实验。
3. **Blind Detection（盲检测）**：重新独立上传接收文件，不传入期望答案，返回 `IDENTIFIED` / `UNKNOWN` / `DECODE_ERROR` 等结果。
4. **Signal Analysis（信号分析）**：查看对齐波形、STFT 时频谱、频谱差异，并在对齐可信时计算 SNR、LSD。

V4 优先在本地 CPU 运行，**并未部署到现有的 Render V3 服务**。神经推理需要另行获取 Sony 官方源码和预训练 checkpoint；仓库不包含、不再分发权重。

## 现有实验结果

| 实验 | 已记录结果 | 注意事项 |
| --- | --- | --- |
| V4 P9：12 个独立来源，每个来源 2 条固定消息 | Clean **24/24**、MP3 128 kbps **24/24** 正确接受 | 有限来源、固定评估协议 |
| V4 P9：AAC-LC/M4A 128 kbps | 原始准确解码 **24/24**；最终正确接受 **23/24** | 一条正确消息被暂定阈值拒绝 |
| V4 P4：4 段精选音频 × 3 个信道 | 独立重新上传盲检 **12/12** 通过 | 浏览器验收及人工听音仍未完成 |
| V4：2026-11-07 发布回归 | Clean/MP3/AAC 均恢复正确消息；**79/79 测试通过** | 单段音乐的 smoke，不是新的泛化测试 |
| 冻结 V3：6 秒 MP3 测试 | **117/120** 正确接受 | 与 V4 使用不同协议 |
| 冻结 V2：MP3 身份识别 | **46/48** | 四身份分类，不等于任意 32-bit 恢复 |

上述是**历史记录的有限规模实验**，不是对任意音频、任意攻击的保证。能执行加噪和裁剪，并不代表这些信道下已验证可靠恢复。神经检测的置信度阈值仍为暂定设置。相关负面结果和协议差异保留在 [V4 实验报告](https://github.com/suibianba12138/blind-audio-watermarking/tree/upgrade/v4-github-prep/docs/reports/v4) 中。

## 本地运行 V4

**必须先切换 V4 分支**，不能直接在 `main` 运行 V4 Studio：

    git clone https://github.com/suibianba12138/blind-audio-watermarking.git
    cd blind-audio-watermarking
    git switch upgrade/v4-github-prep

请准备独立的 **Python 3.12+** 虚拟环境、FFmpeg（含 `ffprobe`、MP3 和 AAC 编码器）、`requirements-v4.txt` 依赖及兼容的 CPU PyTorch。同时从 [Sony 官方仓库](https://github.com/sony/silentcipher) 获取 SilentCipher 源码和 44.1 kHz checkpoint，检查上游使用许可，并将文件保存在仓库外部。

    export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
    export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
    export V3_SOURCE_ROOT="$PWD"
    export V4_STUDIO_PYTHON=python
    bash scripts/run_v4_studio.sh

启动后访问 **http://127.0.0.1:7862**。Studio 仅绑定本机地址，不提供公网分享。详细的依赖、复现步骤和模型限制请看 [V4 README](https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/README_ZH.md) 与 [V4 复现说明](https://github.com/suibianba12138/blind-audio-watermarking/blob/upgrade/v4-github-prep/docs/V4_REPRODUCTION.md)。本地实测环境不能当成 Sony 官方支持的完整依赖矩阵。

### 运行当前 `main`（V3/Legacy）

以下命令只对应 `main` 上的历史传统 DSP 系统（Python 3.10+、FFmpeg）：

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[gui,dev]'
    python examples/generate_test_audio.py --output /tmp/watermark_test_signal.wav
    python scripts/demo.py --input /tmp/watermark_test_signal.wav --identity UESTC-003 --codec mp3
    python -m app.gui

**这里启动的是 V3/Legacy GUI，不是 V4 Studio。**

## 验收状态与边界

- 2026-11-07 的 V4 回归记录：自动化测试 **79/79**，单段真实音乐 Clean / MP3 / AAC 独立文件重新上传盲检成功。**真实浏览器中的视觉/交互验收和人工 A/B 听音仍待完成**。
- P9 只有 12 个独立音频来源，不足以证明广泛鲁棒性、音质透明度或正式的误接受率上界。
- 公开身份水印不能用作密码学意义上的版权认证，恶意伪造/移除及跨场景泛化尚未得到系统验证。
- 原创项目代码采用 [MIT License](LICENSE)。Sony SilentCipher 为第三方软件，权重单独再分发条款尚未明确，**本仓库不包含权重**。第三方测试音频不公开再分发。
- V2/V3 的历史方法、结果和限制分别见 [METHOD](docs/METHOD.md)、[RESULTS](docs/RESULTS.md)、[LIMITATIONS](docs/LIMITATIONS.md)。

---

<div align="center"><sub>Robust Audio Watermarking Studio · 数字信号处理课程设计 · 版本明确，结果可追溯。</sub></div>
