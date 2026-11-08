# V4-P0 可行性与官方模型最小复现报告

**审查日期：2026-11-04（Asia/Shanghai）**\
**判决：`V4_P0_DECISION = CONDITIONAL_GO`**\
**证据边界：官方源码/配置已核查；一段音乐上的 clean 与真实 MP3 链路为 `RUNTIME_PASS`；语音、环境声、裁剪和统计性能仍为 `NOT_VERIFIED`。**

## 1. 范围与保护边界

本轮只做 V3/V4 工作区盘点、SilentCipher 代码与模型审查，以及一段真实音频的 CPU 推理。没有训练模型、修改 V3 算法、修改 Render 服务、下载无关数据或推送 GitHub。

- 当前根工作区是 `main @ 2df4e02f`，未配置远端；工作区已有 3 个已修改文件和 1 个未跟踪审批文件，均未触碰。
- 历史 V3 工作区是干净的 `feat/v3-8bit-integration @ 7fe678234e8af1d0be34a0a3e56297c7182945ff`；只读查询确认其远端同名分支当前仍指向该提交。远端 `main` 为 `1641cebc…`，不以它替换冻结 V3。
- 独立 V4 工作区是干净的 `research/v4-p0 @ 042ce9e`；远端没有同名 `research/v4-p0` 分支，本轮不推送。
- 新增文件只写入独立 V4 工作区。Sony 源码、权重和临时环境保存在 `/tmp`，没有进入 Git。

## 2. 官方模型审查

### 来源、版本、许可与权重

审查并运行的官方仓库提交为 `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`。Sony GitHub release `release` 提供 `Models.tar.gz`，GitHub API 标示 64,389,731 bytes；本地下载长度相同，完整 gzip/tar 校验通过。发布 API 没有提供资产 SHA-256，故记录本地 SHA-256 `cd2beaa9824102c4bae5fe9de7b737cda2682b109ab5f2375a72f3303172af78` 作为本次文件身份值，而不称其为上游签名校验。

44.1 kHz 目录为 `Models/44_1_khz/73999_iteration`，核心权重约 11 MiB（`enc_c.ckpt`、`dec_c.ckpt`、`dec_m_0.ckpt`）；归档内还含 16 kHz 模型及优化器状态。三个实际使用 checkpoint 的 SHA-256 已写入 `experiments/v4_p0/SILENTCIPHER_REPRODUCTION.json`。测试以本地明确 checkpoint/config 路径加载，没有触发 Hugging Face 自动回退下载。

官方代码仓库的 `LICENSE` 是 MIT。README 没有明确说明独立发布权重文件是否沿用同一许可，也没有随模型归档提供独立 license 文件；公开发布/再分发 checkpoint 前需再确认权重许可范围。

### 架构、音频接口和容量

官方 API `get_model(model_type='44.1k', device='cpu')` 返回编码/解码模型。配置 `SR=44100`、`N_FFT=4096`、`HOP_LENGTH=2048`、`message_band_size=1024`、`n_messages=1`、`message_len=21`、`message_dim=5`、默认 `message_sdr=47 dB`，训练音长配置为 12 秒。文件和 waveform API 都支持；waveform 需给出采样率，可单声道或多声道。模型会把非 44.1 kHz 输入重采样至内部采样率，再将嵌入结果转回输入采样率。多声道按声道嵌入，每声道承载一个消息。

消息是 5 个 8-bit 整数，即 40 bit/声道。源码把字节拆成 20 个 2-bit 符号并附加终止符，然后沿 STFT 时间帧重复，解码以帧间众数恢复符号。因此它不是任意长度的字节流协议，也没有在本轮验证更长消息/多声道容量。

实现对幅度谱做卷积式编码与消息条件化的谱扰动，解码器从输入音频 STFT 幅度直接恢复重复消息符号；合成使用原始 STFT 相位。公开论文/README 描述了心理声学阈值和伪可微编解码增强；本次采用 release 默认配置，不独立验证训练机制或论文级结论。调用 `decode_wav(marked, sr, ...)` 不需要原音频，具备真正的盲解码接口。

### 压缩、裁剪和媒介适配

发布配置包含 MP3、AAC、OGG 64/128/256 kbps augmentation 字段。这表明这些失真进入训练配置，不等同于所有媒介上都已独立验证。README 说明可通过 `phase_shift_decoding=True` 搜索 STFT hop 内相位偏移，以应对裁剪；该搜索会明显增加解码时延。本轮未执行裁剪测试。

官方 `decode_wav` 返回 `messages`、逐帧一致度 `confidences` 和 `status`，但没有公开校准的统一水印存在阈值。源码中的 `status=True` 主要表示解码流程成功，不是经校准的 presence 判决；未检测到符号时会返回失败。系统应用仍需用独立负例/目标误警率制定检测策略。

### 依赖与安全

官方 requirements 声明 Python `>=3.8`，但同时要求 `scipy>=1.11.4` 和 `torch<=2.0.0`。SciPy 1.11.4 的 Python 版本要求排除 Python 3.8；现有机器人环境为 Python 3.8.20 / Torch+Torchaudio 2.3.1，也超出官方 Torch 上限。官方代码执行 `torch.load` 时未显式指定 `weights_only`；本轮使用 Torch 2.14.0，PyTorch 的默认 weights-only 加载可成功读取这些 state dict。若未来选用旧版 Torch 以符合上游约束，需要显式采用安全 state-dict 加载并确认模型兼容性，不能无审查地反序列化任意 checkpoint。

## 3. 环境与资源可行性

| 项目 | 审计结果 |
|---|---|
| 默认 Python | 3.13.5；无 Torch/Torchaudio |
| `unitree-rl` | Python 3.8.20、Torch/Torchaudio 2.3.1、无 CUDA；未修改 |
| `hsmujoco_py312` | Python 3.12.14、Torch 2.14.0+cpu、无 Torchaudio；只复用 Torch |
| 实验隔离环境 | 临时目录中的 Python 3.12 venv + system-site Torch；增加固定版本 librosa 0.10.2.post1、soundfile 0.13.1 等音频依赖 |
| CPU/GPU | AMD Ryzen 7 8845H，16 逻辑 CPU；CUDA unavailable，无可用 NVIDIA GPU |
| RAM/磁盘快照 | 27 GiB 总内存、审计时约 11 GiB available；磁盘约 40 GiB available |
| FFmpeg | 6.1.1，含 `libmp3lame` |
| 机器人环境改动 | 否；没有在其 Python/Conda 环境安装、升级或降级包 |

推理在 Python 3.12 + Torch 2.14 CPU 上实测成功，但它不符合上游声明的 Torch `<=2.0.0` 区间。结果说明当前 CPU 有推理能力，不代表该组合已获上游支持。一个进程峰值 RSS 约 1.60 GiB；页面服务需限制并发/排队。模型加载计时约 0.041 秒为热文件缓存的模型构造与权重加载，不包含 Python/Torch 导入；保存后的复现脚本重跑整进程墙钟为 28.61 秒。

## 4. 最小实测结果

素材为 MUSAN 古典音乐单声道片段，源文件 16 kHz；按官方模型输入先重采样至 44.1 kHz，取/补齐为 12 秒。消息为 `[83, 67, 86, 52, 7]`。这是单样本工程检查，不是性能统计。

| 实验 | 输入与过程 | 结果 | 时延 |
|---|---|---|---:|
| 1. 无攻击 | 12 秒音频 → 40-bit 嵌入 → 盲检测 | `status=True`；消息完全一致；confidence 0.9802；测得嵌入 SNR 48.6233 dB，模型报告 SDR 48.6233 dB | 嵌入 3.868 s；检测 6.985 s |
| 2. 真实 MP3 | 嵌入 WAV 写为 PCM16 → FFmpeg `libmp3lame` CBR 128 kbps → 解码为 PCM float → 盲检测 | `status=True`；40-bit 完全恢复；confidence 0.9841；MP3 193,141 bytes | 检测 7.036 s |
| 3. 无水印负例 | 同一未嵌入源音频直接送检测器 | `status=False`，无消息输出；单负例观察，不能当误警率 | 检测 6.942 s |
| 4. 资源 | 同一探针进程，Torch CPU 线程数 4 | 峰值 RSS 1,680,200 KiB（约 1.60 GiB）；整进程墙钟 28.61 s | 模型热缓存加载 0.041 s |

裁剪：`NOT RUN`。官方通过 hop 内搜索做 phase-shift decoding，并明确提示会显著增加时间；单次普通检测约 7 秒，本轮先不把代价扩展成攻击测试。

逐项原始输出见 [SILENTCIPHER_REPRODUCTION.json](../../../experiments/v4_p0/SILENTCIPHER_REPRODUCTION.json)，可复现实验脚本见 [v4_p0_silentcipher_probe.py](../../../experiments/v4_p0/prototype/v4_p0_silentcipher_probe.py)。本轮输出未保存音频，也没有把模型权重或 MUSAN 文件复制进仓库。

## 5. 与 V3 的初步差异

| 项目 | V3 冻结基线 | SilentCipher 本轮证据 |
|---|---|---|
| 名义有效消息 | 8 bit | 40 bit/声道 |
| 原生设置 | 6 秒、48 kHz 单声道 | 12 秒模型配置、44.1 kHz；单声道测试 |
| 无攻击/MP3 | 用户提供的独立历史 MP3 128 kbps 117/120（97.5%） | 本轮同一条音乐片段 clean 与 MP3 均精确恢复，1/1 |
| 嵌入质量 | 本轮没有重跑/没有同协议 SNR | 本轮单条音乐 SNR 48.62 dB |
| CPU 代价 | 传统 DSP | 12 秒单次检测约 7.0 s，进程峰值约 1.60 GiB |

SilentCipher 名义消息位数是 V3 的 5 倍，但模型配置音长是 2 倍，消息编码/检测协议、采样率、素材、攻击集和负例校准也不同。故 1/1 不能与 117/120 排名，SNR 也没有 V3 同条件对照。当前仅证明其代码与发布权重能跑通，并显示值得继续验证的容量/压缩潜力；没有证明语音/环境音泛化、裁剪鲁棒、稳定误警率或整体优于 V3。

## 6. 最终决策与建议

```text
V4_P0_DECISION = CONDITIONAL_GO
SILENTCIPHER_AS_V4_PRIMARY_ENGINE = PROMISING_CANDIDATE; NOT_YET_COMMITTED
CPU_INFERENCE = RUNTIME_PASS; SINGLE_WORKER/QUEUED INTERACTIVE USE IS PLAUSIBLE
OFFICIAL_TORCH_COMPATIBILITY = NOT_VERIFIED (tested 2.14.0; upstream says <=2.0.0)
VOICE_ENVIRONMENT_CROP_GENERALIZATION = NOT_VERIFIED
V3_STABILITY = PRESERVED
```

- **能否作为 V4 主引擎：**可以作为首个神经水印后端候选，但尚不能冻结为唯一主引擎。应保留 V3 回退与对照路径，等待匹配协议的 P1 结果及 checkpoint 许可确认。
- **CPU 是否够完整课程设计：**足以做单 worker 的课程演示、试听和 DSP 分析；当前约 1.7 GiB 峰值、12 秒检测数秒级，需模型单例加载、任务排队、限制并发。未验证并发服务、长音频和 phase-shift crop 交互时延。
- **是否考虑其他模型：**P0 不启动第二候选复现。仅在 P1 发现许可证、Torch 兼容、负例拒绝、裁剪性能或素材覆盖无法满足要求时，再对一个候选做有界替代审查。
- **V4-P1 首要验证：**冻结一份 source-disjoint 小清单（语音/音乐/环境声各若干段），统一 6 秒/12 秒裁切规则，按 V3 8 bit 和 SilentCipher 40 bit 分开报容量；做 clean、FFmpeg MP3 128k、一个轻量裁剪偏移、无水印负例，测 exact recovery、帧置信度分布、误接受/拒绝、SNR/LSD、CPU 时延/RSS。先核对模型许可与 Python/Torch 可复现性，再制定同源配对比较；不把这些小样本当正式性能声明。
- **完整系统架构建议：**保持冻结 V3 DSP 引擎，新增可插拔神经引擎适配器；共用显式采样率/声道预处理、STFT/波形/频谱显示、MP3/AAC 信道、SNR/LSD 与听音工作流；盲检测输出消息、置信度和独立校准的 presence 决策；模型加载放在单 worker/队列。UI 和部署等到 P1 通过后再做，不把 SilentCipher 内部细节暴露给普通使用者。

### 官方来源

- [Sony SilentCipher 官方仓库与 README](https://github.com/sony/silentcipher)
- [官方 Python 依赖声明](https://github.com/sony/silentcipher/blob/master/requirements.txt)
- [官方发布页与模型归档](https://github.com/sony/silentcipher/releases/tag/release)
- [官方仓库 MIT LICENSE](https://github.com/sony/silentcipher/blob/master/LICENSE)
