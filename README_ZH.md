# Robust Audio Watermarking Studio

> **V4 项目展示主页：** https://shengkaini.com/blind-audio-watermarking/ — 以 40-bit 神经音频水印为主，展示真实 MP3/AAC 实验结果、系统流程及 V2/V3 沿革。页面为**静态实验结果展示**，不执行 V4 在线模型推理。
>
> **V3 真实在线演示：** https://blind-audio-watermarking-demo.onrender.com/ — 保留的传统 DSP/Legacy 在线系统，首次访问可能需要冷启动。
>

这是一个以本地运行优先的课程设计项目，包含两个相互独立的盲音频水印后端：Sony 提供的第三方 SilentCipher 预训练模型，以及仓库内冻结的 V3 DSP 基线。V4 Studio 将音频处理、真实编解码、盲检测和信号分析整合在一个 Gradio Blocks 界面中。

> SilentCipher 是 Sony Research 的第三方模型，不是本项目原创模型。其官方代码采用 MIT 许可；公开的 checkpoint 归档没有清晰的独立权重许可说明，因此本仓库不打包或再分发权重。

## Studio 页面风格与交互流程

V4 Studio 采用与 [Embodied Semantic Communication 项目展示页](https://shengkaini.com/embodied-semantic-communication/)一致的**简约学术项目风格**：浅灰白背景、深灰蓝文字、青绿色强调色、细边框卡片、等宽技术标签和宽松的页面留白。两者是相互独立的课程项目；V4 不依赖参考网站的脚本或素材，只复用视觉语言。

四个标签页对应完整的实际实验流程：

| 页面 | 操作 | 输出 |
| --- | --- | --- |
| **01 · Watermark** | 上传音频，选择 Neural 40-bit 或 V3 8-bit，输入消息 | 原音/水印音试听、WAV 下载及嵌入信息 |
| **02 · Channel Lab** | 重新上传水印文件，进行 MP3/AAC、噪声或裁剪处理 | 真实处理后的文件、播放与信道信息 |
| **03 · Blind Detection** | 独立上传接收文件，选择检测后端 | \`IDENTIFIED\`、\`UNKNOWN\` 或 \`DECODE_ERROR\`，诊断候选和置信度 |
| **04 · Signal Analysis** | 上传原音和处理后文件，设置最大对齐偏移 | 波形、STFT 幅度谱、频谱差异，以及可信对齐下的 SNR/LSD |

界面美化不更改判决规则：低于临时置信度阈值的候选仍显示为 \`UNKNOWN\`；噪声和裁剪选项不能被解释为已经验证鲁棒。主题使用 Gradio 内的本地 CSS 与静态 HTML，不加载外部字体、脚本或 CDN。

**验收状态：** 新版界面仍需要在真实浏览器中检查桌面/移动端布局、音频播放与下载、长文本和图表溢出。自动化组件与 CI 测试不能代替视觉验收；人工 A/B 试听也尚未完成。

## V4 功能

- **Watermark：**SilentCipher 40-bit（5 字节）、单声道 44.1 kHz / 12 秒；或冻结 V3 8-bit、单声道 48 kHz / 6 秒。
- **Channel Lab：**真实 FFmpeg MP3 128 kbps、AAC-LC/M4A 128 kbps 编解码往返、固定随机种子的加性噪声和定长裁剪。提供一种信道操作不代表水印一定能抵抗它。
- **Blind Detection：**单独上传接收文件，使用所选后端的检测策略。SilentCipher 当前阈值仍为 provisional；检测器不会接收预期消息或嵌入会话信息。
- **Signal Analysis：**对齐波形、STFT 幅度谱和差异图、SNR、LSD 与音频元数据。对齐不可信时不提供具有误导性的质量指标。
- CPU 优先、模型单例、有限单 worker 队列、本机绑定、上传/时长限制和过期临时文件清理。

## 当前证据摘要

以下结果是有限的工程检查，不是 SOTA 声明，也不是总体性能保证。

- P9 使用 12 个独立来源、每来源两条固定消息。Clean WAV 和 MP3 128 kbps 的正确接受恢复均为 24/24。AAC/M4A 原始消息解码为 24/24，正确接受为 23/24；有一条完整正确消息因冻结 provisional 阈值而被拒绝。在这些测试中未观察到被接受的错误消息。来源数量较少，不能据此给出正式误接受率。
- P4 选取的 4 段演示素材（音乐 2、语音 1、环境声 1）各自通过 Clean、MP3、AAC/M4A 独立重新上传盲检，共 12/12。该轮验收仍为 **PARTIAL**：未完成浏览器端完整交互验证，也未完成人工 A/B 听音。
- 更早的 P1/P3 失败、AAC ADTS priming 诊断和修正后的 M4A 协议均保留在报告中，包含负面结果和协议差异。

2026-11-07 的 Gradio 升级 smoke 使用 Python 3.13.5、CPU PyTorch 2.14.0、Gradio 6.31.0 和 FFmpeg 6.1.1。对一段已保存且许可明确的原生 44.1 kHz 音乐重新嵌入了新的 40-bit 消息；Clean WAV、MP3 128 kbps、AAC-LC/M4A 128 kbps 均经下载后独立重新上传，并以 `IDENTIFIED` 恢复正确消息。未水印原音返回 `UNKNOWN`，非法音频返回 `DECODE_ERROR`，Signal Analysis 返回对齐图形和指标。该单来源结果只是发布回归 smoke，不是新的性能统计。自动化测试 79/79 通过。由于主机 Snap/AppArmor 限制，已安装的浏览器启动器无法运行，因此浏览器可视和点击验收仍待完成；本地 API/回调通过不等于浏览器验收通过。

报告见 [`docs/reports/v4/`](docs/reports/v4/)，脱敏后的文本实验记录见 [`experiments/`](experiments/)。音频、生成文件、checkpoint 和模型归档均不包含在仓库中。

## 本地运行

请使用独立 Python 环境（Python 3.12 或更新版本，并确保与所选 CPU PyTorch 版本兼容），不要将这些依赖安装到 V3/机器人环境。此前四来源端到端验收使用 CPU PyTorch 2.14.0、Gradio 4.44.1、FFmpeg 6.1.1 和 Sony SilentCipher 1.0.4 源码。本次发布准备将界面升级到 Gradio 6.31.0，并以真实模型重新验证一段音乐的嵌入、Clean/MP3/AAC 文件重新上传盲检、负例及信号分析（见上方日期 smoke）。这是一条样本的回归，不替代 P4/P9 评估结果。该 PyTorch 组合不同于 SilentCipher 上游发布的 `torch<=2.0.0` 要求，是工程实测而非上游支持矩阵。

1. 安装含 `ffprobe`、`libmp3lame` 和 AAC 支持的 FFmpeg。
2. 创建并启用独立的 Python 3.12 或更新版本虚拟环境。
3. 安装 [`requirements-v4.txt`](requirements-v4.txt) 中的 Studio 依赖，再在该环境安装兼容的 CPU PyTorch。Gradio 会解析匹配的 client 和 Web 依赖，不要额外固定旧版 Gradio 间接依赖。
4. 从 [Sony 官方仓库](https://github.com/sony/silentcipher) 和[官方模型发布页](https://github.com/sony/silentcipher/releases/tag/release)获取源码与 44.1 kHz 权重。下载和使用模型前请自行审阅上游条款；不要把模型文件放入本仓库。
5. 设置外部路径并在本机启动：

```bash
export SILENTCIPHER_SOURCE_ROOT=/path/to/official/silentcipher
export SILENTCIPHER_MODEL_DIR=/path/to/official/44_1_khz/73999_iteration
export V3_SOURCE_ROOT="$PWD"
export V4_STUDIO_PYTHON=python
bash scripts/run_v4_studio.sh
```

打开 `http://127.0.0.1:7862`。程序不会启用 Gradio 公共分享，并绑定 localhost。V4 Studio 界面已更新到 Gradio 6.31.0；CPU 模型运行仍需要外置 SilentCipher 源码和权重。联网暴露前必须另行进行安全审查。

模型来源、文件清单、CPU 环境和复现限制见 [`docs/V4_REPRODUCTION.md`](docs/V4_REPRODUCTION.md)。

## 测试

先按 `requirements-v4-dev.txt` 安装 pytest 开发依赖，再运行以下测试。

```bash
PYTHONPATH=src:. python -m pytest tests/test_silentcipher_adapter.py tests/test_v4_p4_audio_processing.py tests/test_v4_p4_backends.py tests/test_v4_pcm16_peak_safety.py tests/test_v4_gradio_compat.py
```

这些是本地代码测试。完整模型运行还需要外部 SilentCipher 源码和权重。

## 历史版本

- **Course V2 发布快照：**[`a89b493`](https://github.com/suibianba12138/blind-audio-watermarking/tree/a89b4935ec056a6709cc17379e333a9b1f7c387e)，保留在仓库 Git 历史中。
- **冻结 V3 8-bit 集成：**[`feat/v3-8bit-integration`](https://github.com/suibianba12138/blind-audio-watermarking/tree/feat/v3-8bit-integration)，提交 `7fe678234e8af1d0be34a0a3e56297c7182945ff`。
- 当前仓库 `main` 已包含 V3 集成和托管演示历史。V4 准备分支从当前历史延续，不重写历史。

## 许可与署名

本仓库项目代码采用 MIT 许可。Sony SilentCipher 官方代码为第三方 MIT 许可；权重归档未包含在本仓库中，且审计时未确认其单独再分发条款。实验使用的第三方音频仅用于本地测试，不由本仓库分发；报告在已知范围内记录来源和许可。依赖和 FFmpeg 各自保留其许可。
