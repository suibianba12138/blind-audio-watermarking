# V4-P5 Neural Audio Watermark Robustness Optimization Report

**日期：2026-11-05**\
**判决：`V4_P5_DECISION = NO_GAIN`**\
**范围：** SilentCipher 官方 44.1 kHz 冻结权重；不训练、不改官方源码/权重、不修改 V3 或 P4 Studio。

## 结论摘要

在 6 个此前未用于 P1/P3 的独立留出来源上，官方硬解码和软时间聚合在默认强度及两个预设强度下均达到 clean `12/12`、MP3 128 kbps `12/12` 的 raw exact 和正确接受；两种解码器均未接受 `6/6` clean 无水印来源或 `6/6` MP3 无水印来源。两条消息是每个来源内的重复测量，独立来源数仍为 6，结果不支持正式误报率或总体性能声明。

软聚合在留出集上没有超过官方硬解码的恢复率。强度从默认 47 dB 降至 43 dB 可修复开发集中的历史失败，但留出集的恢复率没有上升，同时平均嵌入 SNR 从 `49.07 dB` 降到 `45.40 dB`、LSD 从 `2.34 dB` 升到 `2.65 dB`。因此目前没有足够的独立证据证明软解码值得集成；全局加大强度的收益不足以抵偿音质代价。

```text
V4_P5_DECISION = NO_GAIN
SOFT_DECODER_HOLDOUT_GAIN = NONE (official and soft tied at ceiling)
LOWER_MESSAGE_SDR_HOLDOUT_GAIN = NONE; AUDIO_FIDELITY_DECREASED
FALSE_ACCEPTS = 0 in this small frozen sample; not a formal FAR estimate
P4_STUDIO_BACKEND = UNCHANGED
```

## 1. 冻结数据与协议

### 留出集冻结

算法实现和 P5 模型推理前，先冻结了 `configs/v4_p5_eval_manifest.json`。其 SHA-256 为 `daadde793d88c305ccea0bba1dffca839ae68e147d69e3b2b4bd402b13937978`。清单固定了 6 个新来源、裁切起点、文件 SHA-256、两条 40-bit 消息、MP3 处理链、检测阈值和唯一三个强度值。清单状态标记为 `FROZEN_BEFORE_P5_ADAPTER_IMPLEMENTATION_AND_MODEL_INFERENCE`。

新本地音乐来源均是 MUSAN 的 16 kHz 文件。没有找到未使用过的本机原生 44.1/48 kHz 音乐。因此留出音乐被按既定流程重采样到模型采样率，只能检验该输入条件下的解码可行性，**不能证明原生高采样率音乐的高频保真度或泛化**。未下载新素材，也没有用升采样 16 kHz 音乐冒充原生高采样率音乐。

| 来源 ID | 类别 | 源采样率 | 起点 / 片长 | SHA-256 | 许可记录 |
|---|---|---:|---:|---|---|
| `music_holdout_01` | 音乐 | 16 kHz | 24 s / 12 s | `51f44c078bc5687f5e0429ccf4692ca545edef746d424bf53b9c115ef310499d` | MUSAN HD Classical，CC BY-SA 3.0 DE |
| `music_holdout_02` | 音乐 | 16 kHz | 32 s / 12 s | `300f6b8767adf3cd03a09a4901088a466efe0ceab2655fb36cedf1b4e48624d3` | MUSAN HD Classical，Public Domain |
| `speech_holdout_01` | 语音 | 16 kHz | 200 s / 12 s | `4036998b90085affda02abf0675a2de2573ec4db57d14a97c40b789765abb49b` | LibriVox，Public Domain |
| `speech_holdout_02` | 语音 | 16 kHz | 360 s / 12 s | `101d4f0edebb3f6656c679788f30a3d74d8cad2c106b8c8b468f64db81a36683` | LibriVox，Public Domain |
| `environment_holdout_01` | 环境声 | 16 kHz | 2 s / 12 s | `844a80aa903f94094daec9e22b73db3e625613a6722384af4d3dc45509732dfd` | SoundBible，Attribution 3.0 |
| `environment_holdout_02` | 环境声 | 16 kHz | 22 s / 12 s | `b978a4cd75fcb7487de465b29e4c84761f206886d668d0d9c3ec35983013bb93` | SoundBible，Attribution 3.0 |

两个固定消息为 `D3916B24E8` 和 `2C6E94DB17`。使用官方 Sony 44.1 kHz `73999_iteration` 权重，片段均为单声道、44.1 kHz、12 秒。MP3 条件是 PCM16 WAV → FFmpeg `libmp3lame` CBR 128 kbps → PCM float WAV 解码。无水印 clean 和 MP3 负例各测试一次/来源。

预设强度只有三档：官方默认 `message_sdr=47 dB`、备选 `45 dB` 和 `43 dB`。两档备选在观察任何 P5 模型输出前写入冻结清单；没有继续搜索参数。使用 P1 provisional presence threshold `0.6805555373430252`，本轮未重选。检测判决需要合法 5 字节候选且 confidence 达到阈值；错误候选仍作为候选诊断记录。

### 开发/回归来源

开发结果仅使用历史来源：P1 `music_03`（保留其原始消息 `123456789A`）和 P3 的 `speech_02`、`music_01`、`speech_03`、`environment_01`（使用 P3 两条固定消息）。共 5 个来源；`music_03` MP3 和 `speech_02` clean/MP3 已知失败被显式保留。开发结果不与最终留出数据混合。

## 2. 解码器审查与实验性实现

### 官方路径的局限

官方 `decode_wav()` 对每帧网络输出做 `argmax`，丢弃非最大类别的分数；之后按完整 21 符号重复块 reshape，对每个符号位置做众数投票。解码器依赖 20 个 2-bit 符号和一个类别 0 终止符。官方 confidence 是所有帧与逐位置众数相符的比例。

两个历史失败体现了两类信息损失：

- `music_03` MP3 的大多数结果缺失终止符，官方最终返回 `status=False`。在多数投票前保留的次高类别分数，可能包含终止符证据，但帧级 argmax 不保留该信息。
- `speech_02` clean 中官方也因终止符缺失而失败。其 MP3 条件曾输出错误消息 `D3916724E8`，说明“成功解析”并不等同于消息正确。

官方解码器把终止符索引、无消息、数值/解析异常汇总进宽泛异常处理；异常时只返回失败状态，正常返回的 `status=True` 也只是得到候选消息的流程状态。本轮没有将 status 当作水印存在判决。

### P5 软聚合

新增隔离模块 `app/v4_p5_decoder.py`。它不修改 SilentCipher 源码或 checkpoint，而是从同一模型帧分数分出两条解析路径：

1. `decode_official_scores()`：逐帧 argmax → 每 21 帧分组 → 逐位置众数 → 官方终止符轮转与 40-bit 消息解析。
2. `decode_soft_scores()`：按相同的完整重复块，把每一符号位置的 5 类原始分数跨时间块求均值 → argmax → 相同终止符与消息合法性检查。

本轮没有做循环排列搜索、没有删除或猜测缺失终止符，也没有用消息答案、文件名或嵌入会话选候选。软解码 confidence 仍使用每帧预测与所选符号的一致比例，并原样套用 P1 provisional threshold。因分数尺度与官方独立校准尚未证明等价，这项做法是保守工程比较，不是新的校准声明。

两个单元用例验证：(a) 合成帧上的硬众数可错而软均值可恢复候选；(b) 无终止符时软路径必须报 `MISSING_TERMINATOR`，不产生合法候选。用官方模型对两个冻结失败来源各做 clean/MP3 小样本复核，隔离硬解析输出与 `decode_wav()` 的候选保持一致；成功解析的 confidence 差仅为 float 量化量级（约 `2.3e-8`）。解析失败时官方不返回 confidence，而隔离诊断器仍保留失败前的帧一致度供分析。

## 3. 开发集：历史失败是否修复

开发集共 9 个消息-来源组合（P1 音乐 1 个消息；4 个 P3 来源各 2 个消息）。同源消息不是独立样本。

| 方法 / SDR | Clean exact | MP3 exact | Clean 正确接受 | MP3 正确接受 | 错误接受 |
|---|---:|---:|---:|---:|---:|
| 官方硬解码 / 47 dB | 7/9 | 6/9 | 7/9 | 6/9 | 0 |
| 软聚合 / 47 dB | 9/9 | 8/9 | 8/9 | 6/9 | 0 |
| 官方硬解码 / 45 dB | 9/9 | 8/9 | 9/9 | 8/9 | 0 |
| 软聚合 / 45 dB | 9/9 | 8/9 | 9/9 | 8/9 | 0 |
| 官方硬解码 / 43 dB | 9/9 | 9/9 | 9/9 | 9/9 | 0 |
| 软聚合 / 43 dB | 9/9 | 9/9 | 9/9 | 9/9 | 0 |

按来源严格检查全部该来源消息均精确恢复：默认 47 dB 时，官方为 clean `4/5`、MP3 `3/5`，软聚合为 clean `5/5`、MP3 `4/5`；43 dB 时，两种方法 clean/MP3 均为 `5/5`。五个来源的 clean/MP3 负例中，两种方法均为 `0/10` 接受。

失败细节：

- **P1 `music_03`：**47 和 45 dB 下，软聚合仍缺 MP3 终止符；43 dB 下官方硬解码与软聚合均恢复 `123456789A`，confidence `.833` 并被阈值接受。这是强度变体修复，不是软解码修复。
- **P3 `speech_02`：**47 dB 下官方 clean 两条消息均缺终止符；MP3 一条错一字节、一条缺终止符。软聚合 raw exact 为 clean `2/2`、MP3 `2/2`，但 confidence 分别约 `.655/.690` 和 `.647/.667`，正确接受仅 clean `1/2`、MP3 `0/2`。因此软路径从网络分数中恢复出了候选，却没有令该来源可靠地通过冻结存在性策略。45 dB 起，两种算法均恢复并接受该来源 clean/MP3 两条消息。

这说明在历史失败上观察到的收益主要来自更强嵌入；软聚合对 speech clean 有 raw recovery 改善，但在冻结 presence policy 下没有对应的 MP3 接受率改善。

## 4. 独立留出结果

留出集为 6 个独立来源、12 个消息-来源重复测量。各方法/强度的结果相同：

| 解码方法 / SDR | Clean raw exact | MP3 raw exact | Clean 正确接受 | MP3 正确接受 | 错误消息接受 |
|---|---:|---:|---:|---:|---:|
| 官方硬解码 / 47 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| 软聚合 / 47 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| 官方硬解码 / 45 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| 软聚合 / 45 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| 官方硬解码 / 43 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| 软聚合 / 43 dB | 12/12 | 12/12 | 12/12 | 12/12 | 0 |

每个来源的两条消息在每个强度/攻击条件均恢复正确；因此 clean 和 MP3 的 source-strict recovery 都为 `6/6`，不是 `12` 个独立来源。留出负例结果按解码器为：

| 方法 | Clean 负例接受 | MP3 负例接受 | 负例候选情况 |
|---|---:|---:|---|
| 官方硬解码 | 0/6 | 0/6 | 各条件 3/6 有合法 5 字节候选但均低于阈值 |
| 软聚合 | 0/6 | 0/6 | 各条件 2/6 有合法候选但均低于阈值 |

官方硬解码留出负例 confidence 范围：clean `.341–.413`，MP3 `.345–.405`；软聚合：clean `.302–.361`，MP3 `.302–.369`。这是少数来源上的观察，不能宣称正式 false-accept rate。负例候选必须保留为诊断信息，即使最终状态是拒绝。

**独立来源增益判断：**软聚合在 6 个新来源上与官方解析持平；所有强度下均处于全成功天花板。留出集没有证明历史失败的修复可以泛化，也没有支持阈值或搜索策略改变。

## 5. 音质、推理和内存

SNR/LSD 比较同一 12 秒、同一采样率下的源片段和干净嵌入输出；先对齐到共同长度。MP3 失真不计入嵌入音质数值。SNR 为时域功率比；LSD 为 `n_fft=4096`、`hop=2048` 的 Hann 窗 STFT 幅度谱 RMS log 差。每个强度有 12 次重复嵌入（6 来源 × 2 消息）。

| `message_sdr` | 平均嵌入 SNR（范围） | 平均 LSD（范围） | 平均 CPU 嵌入时间（范围） |
|---:|---:|---:|---:|
| 47 dB | 49.07 dB (48.65–49.44) | 2.34 dB (1.38–3.24) | 3.31 s (3.27–3.43) |
| 45 dB | 47.18 dB (46.78–47.58) | 2.49 dB (1.45–3.43) | 3.30 s (3.25–3.34) |
| 43 dB | 45.40 dB (45.03–45.85) | 2.65 dB (1.54–3.59) | 3.29 s (3.25–3.34) |

在 4 Torch CPU 线程下，84 次独立输入前向（72 个正例条件 + 12 个负例条件）平均 `5.74 s`，范围 `5.63–6.10 s`。官方解析和软解析共用这次前向；软解析的 NumPy 后处理时延未单独基准化。独立 `decode_wav()` parity smoke 的整函数耗时 `5.63–5.68 s`，与纯 STFT+网络计时接近。模型导入/初始化/权重加载测得 `0.54 s`（暖缓存进程测量）；进程峰值 RSS `1,583,060 KiB`，约 `1.51 GiB`。

模型 checkpoint SHA-256 与 P0/P1 身份一致：

- `enc_c.ckpt`: `ff64f80d2391fdfc888e4103c499be4a2c958e59626587a1eab6db93204814c7`
- `dec_c.ckpt`: `c23b57635172b2fbd3a8531d15ba76b5885a10d0fe902ccb823c521c56041b33`
- `dec_m_0.ckpt`: `829540c058270d29788f05294894d45bf436e44add0e1099422242ebb94b7088`

降低 `message_sdr` 的确增加嵌入扰动：47→43 dB 时平均 SNR 降约 `3.67 dB`，LSD 增约 `0.30 dB`。独立留出准确率没有提升，因此不推荐将 43 dB 设为全局默认值。主观听感未做正式盲听评测。

## 6. 运行产物与复现

- `app/v4_p5_decoder.py`：隔离软时间聚合和官方硬解析参照。
- `tests/test_v4_p5_soft_decoder.py`：软聚合与终止符保护单元用例。
- `scripts/v4_p5_robustness.py`：P1/P3 开发回归和冻结留出实验入口。
- `configs/v4_p5_eval_manifest.json`：模型推理前冻结的数据、消息、阈值和强度协议。
- `experiments/v4_p5/DEVELOPMENT_RESULTS.json`：历史开发/失败来源逐条原始记录。
- `experiments/v4_p5/HOLDOUT_RESULTS.json`：新来源逐条原始记录及权重/清单身份。
- `experiments/v4_p5/OFFICIAL_PARSER_PARITY.json`：官方 `decode_wav()` 定向一致性检查。

在此前 P2 隔离 Python 环境中运行脚本需由操作者在本机设置 `SILENTCIPHER_SOURCE_ROOT`、`SILENTCIPHER_MODEL_DIR`、`V4_P1_MUSIC_ROOT`、`V4_P1_MUSAN_ROOT`、`V4_P3_MUSAN_ROOT`，并确保 FFmpeg 可用；清单和脚本不包含个人绝对数据路径。权重不复制到仓库。单元测试执行：

```bash
PYTHONPATH=. pytest -q -o cache_dir=[local path omitted] tests/test_v4_p5_soft_decoder.py
```

结果：`2 passed`。实验脚本输出每来源逐条 JSON，重跑会重新进行 CPU 推理和真实 MP3 编解码；它不会改写 P0–P4 结果。

## 7. 限制和工程建议

1. 留出集仅 6 个来源，且未覆盖未使用的原生 44.1/48 kHz 音乐；0 个负例接受不能转换成可信总体误报率。
2. 留出集所有强度、解码器均 100% exact，存在明显天花板效应；不能据此说软解码“等效”或证明弱强度在任意数据上无损。
3. soft confidence 沿用了官方帧一致度语义，并非独立重新校准；本轮不改变阈值。
4. P5 未测试裁剪、AAC、时间偏移或其他编辑，也未比较 V3。P4 Studio 和 V3 冻结基线未修改，P5 候选没有自动接入正式后端。
5. 新模型算法没有必要性证据：软解码在独立来源上无增益，强度变体则用明显音质损失修复特定开发失败。

**建议：**不把软聚合或 43 dB 强度集成到 P4 默认后端。保留 P5 适配器和原始证据作为实验候选；当前继续使用 P4 冻结 SilentCipher 默认配置及其独立 presence 策略，并如实展示 `UNKNOWN`。只有取得来源独立、尤其含原生高采样率音乐的失败样本，且修复能在冻结留出集增加正确接受、同时维持负例拒绝和可接受音质时，才重新考虑算法集成。

本轮未改 V3、SilentCipher 源码/checkpoint、P4 Studio、Render 或 P0–P4 报告/结果；未训练、未下载新数据、未推送 GitHub。
