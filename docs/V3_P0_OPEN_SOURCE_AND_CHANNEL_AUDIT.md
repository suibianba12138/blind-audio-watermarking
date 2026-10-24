# V3 P0 开源算法与原始通道审计

日期：2026-10-24（Asia/Shanghai）
分支：`research/v3-p0`
基线：`main@a89b493`，独立 worktree `/home/nsk/blind-audio-watermarking-v3-p0`

## 1. 审计边界

本阶段只新增审计脚本、实验性原型、测试和文档。`src/audio_watermark/embed.py`、
`detect.py`、`b1.py`、`course_v2.py` 以及 Course V2 / SPL 历史数据没有修改。
没有部署 Render、修改公开网页、复制第三方源码或下载大型数据集。

本文中的合成音频结果仅用于通道诊断和开发原型的 smoke test，不能替代音乐、语音、
环境音的合法独立数据集评估。

## 2. P0-A：冻结 QIM 通道

### 2.1 统计量和格点

对某一 FFT frame 的 carrier A/B 两侧，冻结 embedder 计算：

```text
D_host = sum(log(|X[A]|)) - sum(log(|X[B]|))
Δ      = 2 * strength
offset = strength       (bit=1)
offset = 0              (bit=0)
D_target = Δ * round((D_host - offset) / Δ) + offset
```

然后把 `D_target - D_host` 对称分摊到 A/B 的对数幅度，保留每个 bin 的相位和
pair midpoint。因而在无攻击的 marked spectrum 上，检测 statistic 理想情况下接近
`+strength` 或 `-strength`；clean host 本身并不位于该二元格点。

检测器只使用 received audio、固定配置和 public selector。它计算 received
`D` 到 bit-0 与 bit-1 两个最近格点的距离差：

```text
statistic = distance_to_zero_lattice - distance_to_one_lattice
bit       = 1 if mean(repetition_statistics) >= 0 else 0
```

当前 B1/REAL_TOP32 使用 32 bit、每 bit 4 次 repetition，即首个完整 payload 需要
128 个非重叠 2048-sample frames。每个 frame 的 selector group 在 1--10 kHz 内选择
64 个 carrier bins（A/B 各 32 个）。

### 2.2 合成通道诊断

命令：

```bash
PYTHONPATH=src:. /tmp/blind-audio-watermarking-public-venv/bin/python \
  scripts/v3_p0_channel_audit.py --output-dir /tmp/v3-p0-channel-audit
```

探针为固定随机种子的 speech-like、music-like、environment-like 合成波形；每种均
使用 UESTC-003 的 32-bit codeword、当前冻结 `strength=1.28` 和真实 FFmpeg
`libmp3lame 128k` 往返。详细逐 bit/逐 repetition 统计保存在运行目录的
`per_observation.csv`，不是发布数据。

| synthetic probe | clean BER | marked SNR (dB) | MP3 BER | MP3 boundary crossing | MP3 repetition statistic correlation | low-energy carrier fraction |
|---|---:|---:|---:|---:|---:|---:|
| speech-like | 0.0 | 71.166 | 0.375 | 0.484375 | -0.0315 | 0.1115 |
| music-like | 0.0 | 70.135 | 0.0 | 0.0078125 | 0.9625 | 0.1317 |
| environment-like | 0.0 | 50.441 | 0.40625 | 0.453125 | -0.0264 | 0.1000 |

这里的 `boundary crossing` 是 marked statistic 到 MP3 statistic 符号改变的比例；
它不是新的 detector，也不是测试集指标。`repetition statistic correlation` 是
四次 repetition 的逐 bit statistic 矩阵的平均两两相关系数；如果离散错误向量
没有方差，则不报告伪造的相关系数。

### 2.3 机制诊断

当前证据支持以下有限判断：

1. **不是 clean host 无法嵌入。** 三种 synthetic probe 的 marked clean BER 都是
   0，marked statistic 被精确推到二元格点附近。
2. **主要瓶颈是 MP3 后的 carrier 对数幅度差漂移。** speech-like 和
   environment-like 在 MP3 后约 37.5%--40.6% bit BER；music-like 探针则没有
   出现 repetition-level 误码。这种类别差异不能用一个全局 BER 概括。
3. **四次 repetition 不必然提供独立证据。** music-like 的 MP3 repetition
   statistic correlation 很高，而 speech/environment 探针接近零或略负；固定
   repetition 数并不能保证错误独立。
4. **低能量 bins 是风险因素而非已证实的唯一原因。** 当前 carrier 中约 10.0%--
   13.2% 的 bin 落在该 frame candidate band 的低能量 10th percentile；它们在
   `log(|X|)` 域中更容易产生较大的相对幅度变化，但本轮没有据此修改冻结规则。
5. **失真频带不均匀但总量较小。** REAL_TOP32 synthetic probe 的 1--3、3--6、
   6--10 kHz log-spectral RMS 约为 0.036--0.044 dB；该数字只说明本探针下的
   频谱修改，不构成听感或感知不可察觉证明。

因此 P0 的原始失败机制可表述为：固定的对数幅度二元格点在 clean host 上可形成
稳定 statistic，但 codec 后的载波差值漂移具有明显的内容依赖性；现有四次重复在
部分内容上相关，不能可靠地把 MP3 漂移平均掉。

## 3. P0-B：开源方法审查

审计只使用上游仓库、官方 README/LICENSE、官方 model metadata；未复制任何第三方
源码。当前环境检查结果：Python 3.13.5，FFmpeg `/usr/bin/ffmpeg` 可用；
`torch`、`torchaudio`、`soundfile`、`librosa`、`wavmark`、`silentcipher`、
`audioseal` 和 `omnisealbench` 均不可导入；`audiowmark` CLI 不在 PATH。向 GitHub
执行 `git ls-remote` 的本地网络探针因代理不可达而失败。

| 项目 | 上游事实 | 许可 / 权重 | 本地状态 | 结论 |
|---|---|---|---|---|
| [audiowmark](https://github.com/swesterfeld/audiowmark) | GPL watermark CLI；1024-sample frames；128-bit message；README 说明 128 kbit/s MP3/OGG 目标；推荐 hash/HMAC payload，并使用 convolutional code | GPLv3-or-later；不能复制进本 MIT 项目 | CLI 不在 PATH，未运行 | 可做隔离 black-box，但不能与 6 秒系统直接等价比较；P0 未复现 |
| [WavMark](https://github.com/wavmark/wavmark) | 16 kHz mono；README 给出 1 秒、32-bit model；应用接口使用 16-bit；前 16 bit 是固定 identification pattern，后 16 bit 是 custom payload | [仓库 LICENSE](https://github.com/wavmark/wavmark/blob/main/LICENSE) 标为 MIT；[公开 HF 权重](https://huggingface.co/M4869/WavMark) 可见约 40.2 MB model artifact | 依赖 PyTorch/torchaudio；当前没有 torch，未下载或推理 | 优先复现对象，但本轮 `BLOCKED_ENVIRONMENT`；不能把 README 指标称为本地结果 |
| [SilentCipher](https://github.com/sony/silentcipher) | 官方 README 支持 16 kHz 和 44.1 kHz；示例为五个 8-bit 字符，即 40-bit；模型从 Releases/HF 获取；需要 CPU/GPU PyTorch 路径 | [MIT LICENSE](https://github.com/sony/silentcipher/blob/master/LICENSE)，权重来源和具体 checkpoint 仍需单独核对 | `torch`/`librosa` 不可用，未运行 | 接口和权重路线可行，但不进入本轮本地比较 |
| [AudioSeal](https://github.com/facebookresearch/audioseal) | 16-bit optional message；localized detector；官方 README 指出默认模型面向 16/24 kHz，48 kHz 对 speech 可能工作；HF checkpoints | 官方 README 声明 code 和 weights 使用完整 MIT；模型与代码需保持独立环境 | `torch` 不可用，未运行 | 可作为后续神经 baseline；不能声称已复现 |
| [CRAW](https://github.com/DavidC1212/craw) | STFT magnitude；Q-Former；MP3/codec/denoiser attack layer；ECC；README 描述 Python 3.8 和 bundled epoch-20 checkpoint | 仓库 README 说是 TimbreWatermarking fork，并列出外部 codec/denoiser；本轮未确认完整许可证链 | 未 clone / 未运行 | `REVIEW_REQUIRED`；不复制其源码或模型，后续需逐项核对依赖和权重许可 |
| [OmniSealBench](https://github.com/facebookresearch/omnisealbench) | benchmark harness；audio models 包含 AudioSeal、WavMark 等；需 PyTorch、模型 checkpoints 和显式 attack protocol | common code MIT，但 README 明确 model licenses vary | 未安装 / 未运行 | 作为后续统一评测框架候选，不是单独 watermark baseline |

上表中的“上游事实”均是外部资料摘要，不是本地复现实验。特别是 WavMark、
audiowmark、AudioSeal 的公开指标不能填写进本项目的本地 BER/SNR 表。

## 4. P0-C：统一评估与数据 provenance

本轮没有下载 MUSAN、LibriSpeech、LJSpeech 或其他大型数据，也没有把未经核实来源
的音频放入仓库。当前仓库没有可审计的音乐、语音、环境音 source recordings，因而：

- `DEV_DATA_STATUS = NOT_ESTABLISHED`；
- `INDEPENDENT_TEST_DATA_STATUS = NOT_ESTABLISHED`；
- 合法来源、许可、source-disjoint split、重复录音检查均未通过；
- 真实音频上的 FPR/FAR、完整消息恢复率、感知质量均不能在本阶段宣称；
- P0 的合成探针不应被称为真实音乐/语音/环境音数据。

统一评估协议已经冻结为：同一 source recording 只进入 dev 或 test 之一；MP3 必须是
FFmpeg 真实编解码；比较时按 marked-vs-clean SNR / 频谱失真等 fidelity budget 对齐，
而不是把不同方法的 strength 数字直接对齐；所有参数先在 dev 选择，再在未使用的
test 上一次性报告；无 rejector 的候选方法 FPR 标记 `NOT_ESTABLISHED`。

## 5. P0-D：自主原型

新增但不接入冻结公开路径的文件：

- `src/audio_watermark/v3_p0.py`
- `scripts/v3_p0_prototypes.py`
- `tests/test_v3_p0_contracts.py`

原型组合了四个要求中的最小可解释部分：

1. keyed time-frequency sign sequence；
2. 每 frame 的局部 log-magnitude normalization；
3. 根据 received-side energy 计算有限权重，避免完全依赖低能量 bins；
4. 对 signed correlation 做 repetition aggregation。

它只支持 1-bit 和 8-bit，使用固定的非重叠 FFT frame，不修改 B0/B1/Course V2。
测试先失败于缺少模块，之后实现并通过 3 个 prototype contract tests。

有限开发 sweep 为 `strength=0.02, 0.04, 0.08`，每个 strength 覆盖三类合成 probe 和
1/8-bit。完整记录见 [`V3_P0_PROTOTYPE_TRIALS.csv`](V3_P0_PROTOTYPE_TRIALS.csv)。
`strength=0.02` 的代表性结果为：

| payload | speech-like MP3 BER / SNR | music-like MP3 BER / SNR | environment-like MP3 BER / SNR |
|---|---|---|---|
| 1 bit | 0.0 / 67.08 dB | 0.0 / 62.17 dB | 0.0 / 44.94 dB |
| 8 bit | 0.0 / 60.89 dB | 0.0 / 55.88 dB | 0.0 / 39.24 dB |

这些结果只证明“原型在合成开发探针上可运行”，不证明优于冻结 B1：

- 没有 rejector，因此 FPR/FAR 未建立；
- 没有合法真实 source recording；
- 没有 independent test；
- 没有正式听感实验；
- 1-bit/8-bit 结果不等价于任意 32-bit message recovery。

## 6. 当前可复现命令

```bash
PYTHONPATH=src:. /tmp/blind-audio-watermarking-public-venv/bin/python \
  -m pytest -q -p no:cacheprovider

PYTHONPYCACHEPREFIX=/tmp/v3-p0-pyc \
  /tmp/blind-audio-watermarking-public-venv/bin/python -m compileall src app scripts tests

PYTHONPATH=src:. /tmp/blind-audio-watermarking-public-venv/bin/python \
  scripts/v3_p0_channel_audit.py --output-dir /tmp/v3-p0-channel-audit

PYTHONPATH=src:. /tmp/blind-audio-watermarking-public-venv/bin/python \
  scripts/v3_p0_prototypes.py --output-dir /tmp/v3-p0-prototypes

PYTHONPATH=src:. /tmp/blind-audio-watermarking-public-venv/bin/python \
  scripts/v3_p0_open_source_audit.py --output /tmp/v3-p0-open-source-audit.json
```

所有 `/tmp` 输出都可删除并由上述脚本重新生成；它们没有作为数据集提交。
