# V4-P6 Advanced Neural Model Comparison Report

**日期：2026-11-05**\
**判決：`V4_P6_DECISION = REJECT`（拒绝 AudioSeal 作为 SilentCipher 的通用主引擎替代）**\
**范围：** AudioSeal 官方冻结 16-bit generator/detector 与 SilentCipher P1 官方默认配置；仅 CPU；无训练、GUI、V3/P4/P5 改动。

## 结论摘要

P6-A 的三类最小链路可运行：AudioSeal 在 clean、真实 MP3 128 kbps 的三个正例上都判定有水印；6/6 无水印输入被拒绝。但 16-bit exact 仅 2/3。冻结的 12 个新来源配对比较进一步显示：AudioSeal 的 clean 与 MP3 exact 都为 `6/12`（音乐 `1/4`、语音 `4/4`、环境 `1/4`），且错误消息仍全部通过其 presence 判决；AAC exact 为 `0/12`。SilentCipher 在同源 clean/MP3 上均为 `12/12` exact/correct-accepted，AAC 为 `0/12` accepted。AudioSeal 的检测明显更快并可检测 4 秒裁剪，但嵌入 SNR 平均约 `26.74 dB`，低于 SilentCipher 的 `48.85 dB`；综合不满足通用主引擎门槛。

```text
V4_P6_DECISION = REJECT
AUDIOSEAL_GENERAL_ENGINE = NOT_ADOPTED
AUDIOSEAL_SPEECH_SPECIALIZATION = PROMISING_BUT_NOT_VALIDATED
P4_STUDIO_BACKEND = UNCHANGED
```

## 1. 官方技术与许可审查

### 模型机制与接口

AudioSeal 使用配对训练的水印生成器与检测器。官方配置为单声道 SEANet（`dimension=128`、`n_filters=32`、2 层 LSTM），输入 waveform `[batch, channels, samples]`，输出同长度加性水印；16-bit 消息作为可选条件编码。检测器输出逐采样点的 presence 类概率和 16 个消息位的软值。官方模型卡将 generator 和 detector 分别标为 `nbits: 16`。模型面向 localized watermarking，检测器可以在收到的音频或局部裁剪上调用；不需要原始音频或嵌入会话。

官方 README 将默认模型的目标输入采样率列为 16 kHz（另提及其他采样率需匹配模型能力）。本轮按 16 kHz 使用，未向模型传入升采样或高采样率以制造公平性。官方介绍将其定位为语音局部水印，因此音乐/环境声结果仅是本轮工程实测，不作一般化推断。[官方 README](https://github.com/facebookresearch/audioseal) · [16-bit generator card](https://github.com/facebookresearch/audioseal/blob/main/src/audioseal/cards/audioseal_wm_16bits.yaml) · [16-bit detector card](https://github.com/facebookresearch/audioseal/blob/main/src/audioseal/cards/audioseal_detector_16bits.yaml)

容量为 16 bit（65,536 个消息编码），对比 SilentCipher 的 40 bit。两者消息长度及官方输入采样率不同，容量不作质量排名。官方 `detect_watermark()` 返回的 presence 值不是由本轮数据校准的概率：官方实现逐采样点将正类概率与 `0.5` 比较，再返回正类采样点占比；同一方法将逐位 detector 输出阈值化为消息候选。官方明确注明无水印输入也会产生随机消息位。因此本实验只用 presence score `>= 0.5` 判决（固定使用 API 默认的检测阈值，不在本轮测试集调参），并单独检查 16-bit exact。高 presence 但消息错误时记为 wrong-message acceptance。

### 版本、权重、许可与加载安全

- PyPI 包：`audioseal==0.2.1`；CPU runtime：PyTorch/torchaudio `2.5.1+cpu`。
- Hugging Face 仓库 revision：`3c19eba53390776cf2cc9ed5f6c9ac67ce72ecba`（`facebook/audioseal`）。权重下载至 `/tmp` 并在加载前匹配官方文件页 SHA-256：
  - `generator_base.pth`: `7a845b5fbe9364a63a3909d8ab3fe064d13a76ae4c2e983573e08c69b7b51748`（58,805,980 bytes）
  - `detector_base.pth`: `8a78e8a83584113523e161fc599fcab10fd0e94c04d2eb9d2fa1e9ec91ab69d9`（34,667,641 bytes）
  - 合计约 89.1 MiB。
- 官方仓库说明 MIT 许可包括模型权重；Hugging Face 模型卡标为 MIT。[官方许可说明与 README](https://github.com/facebookresearch/audioseal) · [官方模型仓库](https://huggingface.co/facebook/audioseal)。本轮未将权重复制到 V4 仓库。
- `.pth` 是 pickle checkpoint，官方 AudioSeal loader 调用 `torch.load(..., weights_only=False)`。因此不是安全张量格式。本轮先锁定公开官方 revision、验证两个 SHA-256，再在独立 `/tmp` 环境调用官方配置、builder 和权重转换/加载函数；仍保留 pickle 风险说明，不建议加载不受信任来源的同类文件。
- SilentCipher 使用 P1/P5 已冻结的 Sony `44.1 kHz / 73999_iteration` 权重与 `message_sdr=47 dB` 默认值，未改 checkpoint。其 40-bit 容量和 P1 provisional presence threshold `0.6805555373430252` 原样保留。

## 2. 环境与执行方式

AudioSeal 在新建的独立 Conda 环境中运行，Python 3.12，CPU-only Torch/torchaudio 2.5.1，NumPy 1.26.4、soundfile 0.14.0、AudioSeal 0.2.1、OmegaConf 2.4.0、einops 0.8.2、Hugging Face Hub 0.28.1。没有修改机器人/旧 SilentCipher 环境或项目依赖文件。SilentCipher 重用既有 P0 运行环境，未安装新包。FFmpeg 6.1.1 提供 `libmp3lame` 和原生 `aac` encoder。两模型均用 4 CPU 线程、单进程，不使用 GPU。

首次尝试系统 Python `venv` 被缺失 `ensurepip` 阻断；随后在临时目录建立独立 Conda 环境。AudioSeal 第一轮把 YAML card 路径误当作 checkpoint，触发 `UnpicklingError`；未修改官方源码或权重。最终从安装包内原始官方 card 读取配置，校验 checkpoint 后使用官方 loader/builder/state-dict 转换流程成功。模型只加载一次并复用。机器有 16 个逻辑 CPU、27 GiB RAM；运行没有出现 OOM。

## 3. 数据与冻结协议

冻结清单为 `configs/v4_p6_source_manifest.json`，其 SHA-256 为 `cc34cd804182df570666cf6c777fcd83c6ed6893c98c7ba9ce06828f9a86d3c6`，在 AudioSeal 模型推理前生成。12 条录音互不重复，并排除 P1/P3/P5 manifest 中已使用的文件 SHA-256。每来源裁取固定 12 秒；每个来源每个引擎只用一条固定消息：AudioSeal `A55A`（16 bit），SilentCipher `D3916B24E8`（40 bit）。来源而非检测记录是统计单位。

所有文件均来自本机 MUSAN 素材及其本地许可记录；源音频未复制进项目。本机没有未使用过的原生 44.1/48 kHz 音乐：12 条源文件全为 16 kHz。AudioSeal 按官方 16 kHz 协议处理；SilentCipher 将 16 kHz 来源重采样到官方 44.1 kHz 输入。因此结果不能证明原生高采样率音乐保真度或泛化。

| ID | 类别 | 相对文件 | 原始 SR / 时长 | 裁切 (s) | SHA-256 | 许可 |
|---|---|---|---|---:|---|---|
| `music_01` | music | `music/fma/music-fma-0000.wav` | 16000 Hz / 297.979 s | 10.0–22.0 | `0f7abd39d9a044e89966d3ff5a60ca0ccdedd076546068af2fb4226e9f774afc` | CC BY 3.0 per local MUSAN FMA LICENSE |
| `music_02` | music | `music/fma/music-fma-0001.wav` | 16000 Hz / 218.044 s | 30.0–42.0 | `ff51c346d1b8663ce83991dcfafd3b91ed5611ba4b7f33d5dfd01ee2c26e557b` | CC BY 3.0 per local MUSAN FMA LICENSE |
| `music_03` | music | `music/fma/music-fma-0002.wav` | 16000 Hz / 249.548 s | 50.0–62.0 | `86e0ea8e63a2a2a07747cfe711e15a8d86c990a2a0035acdb426dc163bbbd320` | CC BY 3.0 per local MUSAN FMA LICENSE |
| `music_04` | music | `music/fma/music-fma-0003.wav` | 16000 Hz / 324.780 s | 70.0–82.0 | `ebb2ef7dbdf7b42c602531529b328474c284557d7c755ef2ec57c7712b670d20` | CC BY 3.0 per local MUSAN FMA LICENSE |
| `speech_01` | speech | `speech/librivox/speech-librivox-0000.wav` | 16000 Hz / 444.029 s | 15.0–27.0 | `6a74f9d017dacbae23e1d6a42f5e29afa52cbc21a4c08e30e86879890e8ad5a8` | Public Domain per local MUSAN LibriVox LICENSE |
| `speech_02` | speech | `speech/librivox/speech-librivox-0001.wav` | 16000 Hz / 79.935 s | 30.0–42.0 | `aa31bcba6049760ee64468437cc11a3d9359a71310f403c27d69ca2f25e9ed12` | Public Domain per local MUSAN LibriVox LICENSE |
| `speech_03` | speech | `speech/librivox/speech-librivox-0002.wav` | 16000 Hz / 253.727 s | 45.0–57.0 | `f907f96e69eb8e680c86964f63ff570d2c24458beacd7d94520c44b2a5c10868` | Public Domain per local MUSAN LibriVox LICENSE |
| `speech_04` | speech | `speech/librivox/speech-librivox-0003.wav` | 16000 Hz / 234.580 s | 60.0–72.0 | `8c1370aaca2843057072ded459deb739413910e7a2c5a1f21d3e04c2b3fe4c6b` | Public Domain per local MUSAN LibriVox LICENSE |
| `environment_01` | environment | `noise/free-sound/noise-free-sound-0000.wav` | 16000 Hz / 17.659 s | 2.0–14.0 | `38624671753649af38f97b5872463017badcb3e29411787a95f6f2beb9edbfec` | Public Domain per local MUSAN FreeSound LICENSE |
| `environment_02` | environment | `noise/free-sound/noise-free-sound-0001.wav` | 16000 Hz / 40.536 s | 10.0–22.0 | `757966dde40b87b2862013eaf0808e47a560e1d3bc9e75167df292313328ab56` | Public Domain per local MUSAN FreeSound LICENSE |
| `environment_03` | environment | `noise/free-sound/noise-free-sound-0002.wav` | 16000 Hz / 71.218 s | 20.0–32.0 | `a4c955e6b759de071e7b71b71d2a2a1dc5392408ef386f3d713f83f71bbf5928` | Public Domain per local MUSAN FreeSound LICENSE |
| `environment_04` | environment | `noise/free-sound/noise-free-sound-0003.wav` | 16000 Hz / 14.236 s | 1.0–13.0 | `d0d6eb43054994b91263d8cc5caf277c9622d2903144347e7f7736b3c228711f` | Public Domain per local MUSAN FreeSound LICENSE |

每引擎分别对其官方预期采样率的 12 秒 mono PCM16 WAV 执行真实 FFmpeg 编码/解码：MP3 `libmp3lame CBR 128 kbps`；AAC 原生 `aac` encoder、128 kbps ADTS。正例条件：clean、MP3、AAC；负例：unwatermarked clean、unwatermarked MP3。AAC 不做负例，本轮最低协议只要求 clean/MP3 负例。

AudioSeal 另取音乐、语音、环境各一个水印样本，从标记后 12 秒音频截取 `t=4–8 s`（4 秒）直接运行 detector；无搜索、无 phase shift。检测器仅接收当前音频和固定模型配置，没有传入真实消息、嵌入会话或 ground truth。消息正确性仅在离线统计阶段与冻结消息比较。

## 4. P6-A：三来源 CPU 最小验证

P6-A 采用 1 个音乐、1 个语音、1 个环境来源。三类 clean 与真实 MP3 的 presence 均接受（6/6），且 clean 与 MP3 的 16-bit exact 各为 2/3。clean 与 MP3 无水印负例共 6/6 拒绝。音乐样本 presence score 为 1.0，但候选 `E55E` 与固定消息 `A55A` 不符。这说明“发现有水印”不能替代“正确恢复消息”。最小运行/presence gate 通过，因此执行冻结的 P6-B；不据此宣称算法可用。

| 来源 | Clean presence / 消息 | MP3 128k presence / 消息 | clean / MP3 negative | SNR / LSD（嵌入） |
|---|---|---|---|---|
| `music_01` | 1.000 / E55E (wrong) | 1.000 / E55E (wrong) | 0.0676 reject / 0.0633 reject | 19.85 dB / 2.28 dB |
| `speech_01` | 1.000 / A55A (exact) | 1.000 / A55A (exact) | 0.0006 reject / 0.0021 reject | 23.94 dB / 1.25 dB |
| `environment_01` | 1.000 / A55A (exact) | 1.000 / A55A (exact) | 0.0000 reject / 0.0000 reject | 36.53 dB / 1.21 dB |

P6-A 首段音乐的 embed 冷启动时间为 57.60 s，后两个来源分别为 0.33 s、0.30 s。12 来源运行再次观察到一次较慢首调用（18.45 s），其余多数 embed 约 0.31–0.35 s。报告保留首次调用延迟，不以 warm-up 时间替代。

## 5. P6-B：12 个独立来源结果

下表格式为“候选十六进制、消息 exact、presence 判决”。`✓` 表示消息 exact，`✗` 表示错误消息。错误消息若通过 presence 仍记为 wrong-message acceptance。

| 来源 | AudioSeal Clean | AudioSeal MP3 | AudioSeal AAC | SilentCipher Clean | SilentCipher MP3 | SilentCipher AAC |
|---|---|---|---|---|---|---|
| `music_01` | `E55E` ✗ / accepted | `E55E` ✗ / accepted | `CC76` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `music_02` | `A55E` ✗ / accepted | `A55E` ✗ / accepted | `CEDE` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | `4F516FE0A0` ✗ / rejected |
| `music_03` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `C512` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | `D391AB54E8` ✗ / rejected |
| `music_04` | `A45A` ✗ / accepted | `A45A` ✗ / accepted | `C752` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `speech_01` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `A6D6` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | `816FA7E0D4` ✗ / rejected |
| `speech_02` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `A0D6` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `speech_03` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `A4D2` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `speech_04` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `A4D6` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `environment_01` | `A55A` ✓ / accepted | `A55A` ✓ / accepted | `E4D6` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |
| `environment_02` | `A45A` ✗ / accepted | `A45A` ✗ / accepted | `C476` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | `5351AC10A8` ✗ / rejected |
| `environment_03` | `B55A` ✗ / accepted | `B55A` ✗ / accepted | `C5D6` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | `B052834281` ✗ / rejected |
| `environment_04` | `A55E` ✗ / accepted | `A55E` ✗ / accepted | `ED36` ✗ / accepted | `D3916B24E8` ✓ / accepted | `D3916B24E8` ✓ / accepted | UNKNOWN (无候选) |

### 按来源类别汇总

- **AudioSeal clean 与 MP3：**音乐 `1/4` exact，语音 `4/4`，环境声 `1/4`；presence 接受 `12/12`。6 个错误消息均被接受。
- **AudioSeal AAC：**`0/12` exact；presence 仍接受 `12/12`，均为 wrong-message acceptance。
- **SilentCipher clean 与 MP3：**每类均 `4/4` exact/correct-accepted，总计 `12/12`。
- **SilentCipher AAC：**`0/12` correct-accepted。7/12 没有合法候选/status 成功；另 5/12 有候选但 confidence `0.5079–0.6230` 低于冻结阈值，因此拒绝。
- **负例：**AudioSeal unwatermarked clean、MP3 为 `0/12` 接受；SilentCipher frozen policy 也是各 `0/12`。SilentCipher raw official `status=True` 偶尔出现在 clean 负例 `3/12`、MP3 负例 `1/12`，但 confidence 低于阈值。故不能把 status 单独作为 presence。

本轮 12 来源仅用于工程选型，不足以声明正式总体误报率。AudioSeal sample-occupancy score 与 SilentCipher frame-consistency confidence 语义不同，不横向比较其数值。

### 消息与 presence 汇总

| 引擎 / 条件 | Raw exact | Correct accepted | Wrong-message acceptance | Presence accepted | Negative acceptance |
|---|---:|---:|---:|---:|---:|
| AudioSeal / clean | 6/12 | 6/12 | 6/12 | 12/12 | — |
| AudioSeal / mp3_128k | 6/12 | 6/12 | 6/12 | 12/12 | — |
| AudioSeal / aac_128k | 0/12 | 0/12 | 12/12 | 12/12 | — |
| AudioSeal / negative_clean | — | — | — | 0/12 | 0/12 |
| AudioSeal / negative_mp3_128k | — | — | — | 0/12 | 0/12 |
| SilentCipher / clean | 12/12 | 12/12 | 0/12 | 12/12 | — |
| SilentCipher / mp3_128k | 12/12 | 12/12 | 0/12 | 12/12 | — |
| SilentCipher / aac_128k | 0/12 | 0/12 | 0/12 | 0/12 | — |
| SilentCipher / negative_clean | — | — | — | 0/12 | 0/12 |
| SilentCipher / negative_mp3_128k | — | — | — | 0/12 | 0/12 |

## 6. 音质与 CPU 资源

SNR/LSD 比较同来源的 12 秒原始裁切与干净嵌入输出，长度对齐，不含 MP3/AAC 失真。SNR 使用时域均方能量比；LSD 使用 `n_fft=4096, hop=2048, Hann` 幅度谱 RMS log 差，epsilon 按源信号峰值固定比例。各模型分别在其官方输入采样率计算（SilentCipher 44.1 kHz，AudioSeal 16 kHz）；因此 LSD 的频率 bin 带宽不同，**跨模型 LSD 仅作近似观察，不作严格公平排名**。

| 引擎 | 平均 SNR（范围） | 平均 LSD（范围） | Embed 时间均值 / 中位数 / 最大值 | Detect 时间均值 / 中位数 / p95 | 模型加载 | Peak RSS |
|---|---|---|---|---|---:|---:|
| AudioSeal | 26.74 (19.85–36.53) dB | 1.66 (1.15–3.55) dB | 1.846 / 0.344 / 18.45 s | 0.336 / 0.336 / 0.385 s | 0.225 s | 1402.50 MiB |
| SilentCipher | 48.85 (48.41–49.62) dB | 2.88 (2.09–3.78) dB | 3.792 / 3.742 / 3.97 s | 6.661 / 6.593 / 7.149 s | 0.040 s | 1560.35 MiB |

AudioSeal detect 中位数约 0.336 s；SilentCipher 约 6.593 s。AudioSeal embed 中位数约 0.344 s，但 18.45 s 首调用将 12 条均值抬高至 1.846 s；P6-A 首调用另测得 57.60 s，反映明显冷启动/CPU 调度波动。SilentCipher embed 中位数约 3.742 s。AudioSeal CPU 速度及局部检测是实测优点，但没有抵消消息错误与低 SNR。FFmpeg 每次 encode+decode 平均约 AudioSeal 路径 0.160 s、SilentCipher 路径 0.201 s。

模型加载时间是在暖文件缓存下由进程计时采集；Peak RSS 是分开进程的 `ru_maxrss` 高水位，包含运行时库，不是模型参数单独内存。

## 7. 局部裁剪检查

AudioSeal 选择三个 P6-A 来源，从水印音频 `t=4–8 s` 截取 4 秒调用 detector：presence `3/3` 接受，exact `1/3`，correct-accepted `1/3`；两条错误消息仍被接受。单次耗时 `0.111–0.161 s`。这验证局部 presence 接口和较低检测成本，不证明任意裁剪都能正确恢复消息。SilentCipher 本轮不运行裁剪搜索；其 12 秒固定解码协议与 phase-shift 搜索不在本轮扩大。

## 8. 失败模式与风险

1. **Presence 和消息恢复脱钩。** AudioSeal 的 12 条 clean/MP3 positive presence score 全为 `1.0`，但 payload exact 只有 `6/12`；AAC score 均值约 `0.981`、exact 为 `0/12`。对必须恢复消息的系统，这是严重 wrong-message acceptance 风险。
2. **类型差异。** 语音 clean/MP3 `4/4` 是值得记录的 speech-oriented 信号；音乐和环境声各 `1/4`。每类仅 4 个来源，不能推断 AudioSeal 仅适用于语音，但当前证据不支持通用替换。
3. **AAC 短板。** 两模型都未在本协议的 AAC 128 kbps 条件正确恢复消息。AudioSeal 仍高 presence 接受错误消息；SilentCipher confidence 低并拒绝。
4. **保真度。** AudioSeal 平均嵌入 SNR 约 `26.74 dB`，远低于本轮 SilentCipher 的 `48.85 dB`。没有进行主观盲听，不能声称听感可接受。LSD 的采样率协议不同，不据此下音质结论。
5. **资源。** AudioSeal detector 快、能本地检测裁剪，但首个 embed 调用延迟波动较大。SilentCipher 慢一些，但 CPU 和内存仍可运行。
6. **素材覆盖。** 无独立原生高采样率音乐，故不能判断 AudioSeal 在原生 44.1/48 kHz 高保真音乐中的表现。
7. **权重加载。** 官方 `.pth` loader 使用 pickle 反序列化；本轮只从官方 Hub 下载并校验哈希，在隔离环境加载。不得将未经审核的 checkpoint 一并打包发布。

## 9. 最终选型与课程系统建议

**AudioSeal 不适合直接成为 V4 通用神经水印主引擎。** 在本轮相同来源上，其 clean/MP3 消息恢复低于 SilentCipher，AAC 都未正确恢复，音质扰动也明显更大。CPU 速度和短片段 presence detection 虽有优势，但高分存在性不能保证消息身份正确。

```text
V4_P6_DECISION = REJECT
```

这里的 `REJECT` 指拒绝其作为通用主算法或 SilentCipher 的直接替代，并非否认 AudioSeal 的 presence/localization 能力。语音 clean/MP3 的 4/4 可作为 speech-specific 候选信号，但来源量小、AAC 失败且没有听感评估，本轮不建议接入正式后端。P4 Studio 继续保留 SilentCipher 默认和 V3 冻结对照；AudioSeal 可留作离线研究对象。若后续考虑局部语音检测，应先明确定义仅 presence 与可靠消息解码的语义边界，再由用户决定是否需要独立专项验证。

本轮未启动 AWARE 或第三模型评估；此后是否审查由用户决定。本轮没有训练、GUI/网站开发、Render 修改或 GitHub 推送。V3、P4、P5 和 P0–P5 原始结果未修改。

## 10. 原始记录与复现依据

- `configs/v4_p6_source_manifest.json`：来源、SHA-256、裁切、采样率、许可、固定消息和实验协议。
- `experiments/v4_p6/AUDIOSEAL_P6A_RESULTS.json`：三来源初测、负例及资源结果。
- `experiments/v4_p6/AUDIOSEAL_RESULTS.json`：12 来源 AudioSeal 逐条输出、presence/message、时延、SNR/LSD。
- `experiments/v4_p6/SILENTCIPHER_RESULTS.json`：12 来源 SilentCipher 配对结果、拒绝/恢复、时延。
- `experiments/v4_p6/MODEL_PROVENANCE.json`：官方 Hub revision、权重 SHA-256 与文件大小。

原始记录不含音频、checkpoint、本机绝对路径或凭证。重跑需要授权的本地 MUSAN 音频及既有 SilentCipher P0 运行环境；AudioSeal 使用独立环境。脚本在推理前检查音频 SHA，加载前检查权重 SHA。
