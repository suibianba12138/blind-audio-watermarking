# V3 — B1 Soft-Code Pilot

状态：`B1_SOFT_CODE_STATUS = PASS_LIMITED_PILOT`

本报告记录一轮有限、预先冻结的 B1-QIM 软判决与短码实验。它不修改冻结的
`embed.py`、`detect.py`、`b1.py` 或 Course V2，也不把本地结果扩展成任意 32-bit
消息恢复、鲁棒性或正式感知质量结论。

## 1. 实验边界与数据

| 项目 | 固定内容 |
|---|---|
| 分支/阶段 | `research/v3-p0` / B1 Soft-Code Pilot |
| 数据 manifest | `configs/v3_b1_soft_pilot_manifest.json`，状态 `FROZEN` |
| 来源 | 本地 MUSAN metadata 指向的真实录音；原始音频不进入仓库 |
| source recordings | 60 条；Speech/Music/Environment 各 20 条 |
| split | 每类 10 dev + 10 test；按源文件/来源组分组 |
| 与 R1 重合 | 0 个 source、0 个 SHA256、0 个相对路径 |
| 消息 | 两个固定 8-bit 消息，seed 101/202；同一 source 上为 paired trials |
| 音频协议 | 48 kHz、单声道、6 秒前缀；与 R1 相同的 source 处理规则 |
| codec | 本机 FFmpeg `libmp3lame`，128 kbps，真实 encode/decode |
| strength | 仅固定评估 `0.96 / 1.28 / 1.60`，未看 test 结果后扩展搜索 |

正式 test 统计单位优先是 source recording；每个 source 的两个消息用于配对观察，
不当作两个独立录音。校准只使用 dev split，test threshold 未重新选择。

## 2. 方法

冻结 B1 的嵌入和物理检测路径保持不变。新增的实验模块只做以下两件事：

1. 暴露已有 QIM signed margin 的连续值，并对四次 repetition 做均值聚合；
2. 将 8-bit 有效消息映射为固定的 `[32, 8, 8]` 二元码，使用 256 个固定码字的
   normalized signed-correlation 做盲解码。

代码本身不把 expected payload、clean audio、真实消息或 ground truth 传入 detector。
expected payload 只在实验脚本完成检测后用于评分。`presence_score` 是诊断/拒绝分数，
不是概率校准值。

对照是相同 32 个物理位上的 8-bit repeat-4 wrapper。两种方法使用同一 source、同一
消息、同一 strength 和同一 MP3 条件；因此可做配对的嵌入失真比较，但没有进行正式
主观听感实验。

## 3. 独立 test 结果

### 3.1 MP3 128 kbps robustness—SNR 曲线

`raw BER` 指 32 个物理位的 BER；`logical BER` 指解码后的 8-bit 有效消息 BER。
`exact` 以 60 个 message trials 为分母；括号中的 source 指两个消息均成功的 source 数。

| 方法 | strength | SNR (dB) | LSD RMS (dB) | physical BER | logical BER | exact | 两消息均成功 |
|---|---:|---:|---:|---:|---:|---:|---:|
| repeat4 | 0.96 | 57.968 | 0.01783 | 0.18854 | 0.12292 | 27/60 (45.0%) | 10/30 |
| soft-code | 0.96 | 58.107 | 0.01779 | 0.19635 | 0.11458 | 45/60 (75.0%) | 19/30 |
| repeat4 | 1.28 | 55.504 | 0.02399 | 0.12552 | 0.06250 | 39/60 (65.0%) | 19/30 |
| soft-code | 1.28 | 55.243 | 0.02386 | 0.12188 | 0.01458 | 57/60 (95.0%) | 27/30 |
| repeat4 | 1.60 | 53.692 | 0.02975 | 0.06667 | 0.02917 | 48/60 (80.0%) | 23/30 |
| soft-code | 1.60 | 53.698 | 0.03010 | 0.07604 | 0.00417 | 59/60 (98.33%) | 29/30 |

在接近相同嵌入失真的配对条件下，soft-code 的物理 BER 并没有改善；改善来自固定
短码对物理错误的聚合。`soft-code@1.60` 比 `repeat4@1.60` 的 SNR 差异约 0.006 dB，
LSD 差异约 0.00035 dB；`1.28` 点的 SNR 差异约 0.261 dB。这里的
`MATCHED_FIDELITY` 仅表示配对嵌入失真检查通过，不表示正式感知质量通过。

### 3.2 类别分解（推荐点 soft-code@1.60）

| 类别 | MP3 exact | logical BER | physical BER | SNR (dB) |
|---|---:|---:|---:|---:|
| Speech | 20/20 (100%) | 0.00000 | 0.06406 | 52.917 |
| Music | 20/20 (100%) | 0.00000 | 0.06563 | 54.582 |
| Environment | 19/20 (95%) | 0.01250 | 0.09844 | 53.595 |
| 总计 | 59/60 (98.33%) | 0.00417 | 0.07604 | 53.698 |

唯一未恢复的 test trial 是 `r1-environment-test-0194-noise-free-sound-0118`、
`seed_101`：physical BER `0.40625`，logical BER `0.25`，presence score
`0.59707`，低于其 dev-calibrated threshold `0.78551`，因此 detector 返回拒绝。
这不是通过缓存答案修正的失败样本。

### 3.3 No-attack

两种方法、三个 strength 和全部 60 个 test message trials 均为 clean exact `60/60`，
physical/logical BER 均为 `0`。这只说明当前 6 秒无攻击条件下嵌入可读，不代表 MP3 或
更长时间/其他 codec 的鲁棒性。

## 4. Rejector 与错误接受

推荐配置为 `soft-code@1.60`。threshold 来自 dev，test 未调参。

| 配置 | clean FPR | clean-MP3 FPR | 合并无水印 FPR | wrong-key MP3 acceptance | positive MP3 wrong-message acceptance |
|---|---:|---:|---:|---:|---:|
| repeat4@1.28 | 2/30 | 2/30 | 4/60 (6.67%) | 1/60 (1.67%) | 17/60 (28.33%) |
| soft-code@1.28 | 3/30 | 1/30 | 4/60 (6.67%) | 2/60 (3.33%) | 1/60 (1.67%) |
| repeat4@1.60 | 1/30 | 1/30 | 2/60 (3.33%) | 2/60 (3.33%) | 10/60 (16.67%) |
| soft-code@1.60 | 0/30 | 0/30 | **0/60 (0%)** | 2/60 (3.33%) | **0/60 (0%)** |

`wrong-key` 的 2/60 接受来自同一个 Music test source 的两条 paired message
尝试，故 source-level 为 1/30；它不是无水印 FPR。负例数量仍不足以证明低于某个
百分比的总体误报率，结果只作为本 pilot 的有限证据。

在推荐点，detector 对 positive MP3 接受 `57/60`；其中 `57` 条 accepted trial
同时 exact，另有 2 条 exact message 被 reject。因而“消息可解码”和“presence 被
接受”必须分开报告。

## 5. WavMark CPU 可行性

本地审计文件：`experiments/v3_b1_soft_pilot/WAVMARK_CPU_AUDIT.json`。

当前 Python 为 3.13.5，FFmpeg 可用，磁盘约 94.05 GiB 可用，但没有 `torch`、
`torchaudio` 或 `wavmark`，也没有本地预训练权重。本轮没有下载、安装或运行 WavMark，
没有把 PyTorch 加入现有 Render/Course 环境。因此：

`WAVMARK_CPU_FEASIBILITY = BLOCKED_NO_LOCAL_DEPENDENCY_OR_WEIGHT`

官方仓库和模型页仅作为后续独立基线的可获取性参考，不是本地复现实验结果：
[WavMark repository](https://github.com/wavmark/wavmark)；
[WavMark model page](https://huggingface.co/M4869/WavMark)。

## 6. 决策

```makefile
B1_SOFT_CODE_STATUS = PASS_LIMITED_PILOT
MATCHED_FIDELITY = PASS_PAIRED_SNR_CHECK_NO_FORMAL_PERCEPTUAL_GATE
RAW_BER = SOFT_CODE_1.60_MP3_0.07604_PHYSICAL; CLEAN_0
EXACT_MESSAGE_RECOVERY = SOFT_CODE_1.60_MP3_59_OF_60_TRIALS_29_OF_30_SOURCES
NEGATIVE_REJECTION = SOFT_CODE_1.60_CLEAN_AND_CLEAN_MP3_FPR_0_OF_60
WRONG_MESSAGE_ACCEPTANCE = SOFT_CODE_1.60_0_OF_60; WRONG_KEY_2_OF_60
WAVMARK_CPU_FEASIBILITY = BLOCKED_NO_LOCAL_DEPENDENCY_OR_WEIGHT
V3_ALGORITHM_DECISION = CONDITIONAL_GO_NARROW_V3_P1_ONLY
```

本 pilot 在相近失真预算下显示：固定 `[32,8,8]` soft-code 对 8-bit 有效消息的
MP3 完整恢复明显优于 repeat-4 wrapper，同时没有在推荐点增加无水印 FPR 或
positive wrong-message acceptance。这满足“有限继续评估”的证据门，但不构成生产
系统或长期研究线的批准。

如果后续重新授权进入窄范围 V3-P1，必须重新冻结新的 source-disjoint validation，
扩大负例并预注册拒绝统计；不得在本 pilot test 上继续调 strength/threshold。不得把
`59/60` 外推为任意 32-bit 消息、任意音频、任意 codec 或正式感知不可察觉性。

## 7. 可复现产物

- `configs/v3_b1_soft_pilot_manifest.json`
- `experiments/v3_b1_soft_pilot/V3_B1_SOFT_CODE_PILOT.csv`
- `experiments/v3_b1_soft_pilot/V3_B1_SOFT_CODE_PILOT_SUMMARY.json`
- `experiments/v3_b1_soft_pilot/V3_B1_SOFT_CODE_CALIBRATION.json`
- `experiments/v3_b1_soft_pilot/WAVMARK_CPU_AUDIT.json`
- `src/audio_watermark/b1_soft.py`
- `scripts/v3_b1_soft_pilot.py`
- `scripts/v3_b1_wavmark_audit.py`

这些结果是本地实验结果；文献/官方项目结果没有混入表格。
