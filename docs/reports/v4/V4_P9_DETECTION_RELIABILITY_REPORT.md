# V4-P9 盲检测可靠性与原生高采样率音频验证报告

**决策：`V4_P9_DECISION = BASELINE_RETAINED`**\
**范围：** 官方 SilentCipher 44.1 kHz / 40-bit / 默认 `message_sdr=47 dB`；官方硬判决解码；P1 冻结的临时 presence 阈值。没有修改权重、阈值、V3、P4 Studio 或 P0–P8 结果。

## 1. 结论摘要

本轮新建了 12 个未与 P1–P8 重合的正例来源：6 个 44.1/48 kHz 音乐录音、3 个语音和 3 个环境声；另有 24 个不同负例录音，音乐、语音、环境声各 8 个。每个正例来源使用两条预先固定的 40-bit 消息。两条消息是同一来源上的重复测量，来源数仍为 12。

| 信道 | Raw exact | Correct accepted | Wrong-message accepted | `UNKNOWN` | `DECODE_ERROR` |
|---|---:|---:|---:|---:|---:|
| Clean WAV | 24/24 | 24/24 | 0 | 0 | 0 |
| MP3 128 kbps | 24/24 | 24/24 | 0 | 0 | 0 |
| AAC-LC / M4A 128 kbps | 24/24 | 23/24 | 0 | 1 | 0 |

AAC/M4A 的唯一拒绝是 `music_commons_01` 的第二条消息：官方解码器候选与固定消息完全一致，官方 `status=True`，confidence 为 `0.674603`，低于冻结阈值 `0.6805555373430252`，所以 presence policy 正确返回 `UNKNOWN`。这是**存在性判决漏检**，不是消息解码错误。6 个新音乐来源在 clean、MP3、AAC 下均为 12/12 raw exact；AAC 音乐的正确接受为 11/12 条消息，5/6 个音乐来源的两条消息都被接受。

24 个负例来源在 clean、MP3、AAC 三种条件下均为 `0/24 IDENTIFIED`、`0/24` 负例接受。负例仍有模型候选：clean 9/24、MP3 4/24、AAC 12/24；这些候选 confidence 全部低于阈值。`status=True` 不能代替水印存在判决。

因此保留 P1 阈值和 P4 默认后端。新来源显示现有策略对这批数据有清晰的正负 confidence 间隔，但 P8 和 P9 均出现了正确消息低于阈值的情况；样本量和数据划分不足以安全选择新阈值或宣称正式 FAR。

## 2. 阈值来源与 P1–P8 历史审查

### 阈值

P1 在开发来源上选择阈值：SilentCipher 开发正例 confidence 最低值为 `0.944444`，开发负例候选 confidence 最高值为 `0.416667`，取两者中点，冻结为 `0.6805555373430252`。P3–P9 均未按各自评价集重选该值。当前策略只有在官方状态为真、存在合法 5-byte 候选且 confidence 达到阈值时才返回 `IDENTIFIED`；其他可解码结果返回 `UNKNOWN`，异常返回 `DECODE_ERROR`。阈值仍为 `PROVISIONAL`，confidence 不是经过概率校准的水印存在概率。

P1 的 `RESULTS.json` 同时含有 SilentCipher 和冻结 V3 的行；本节 SilentCipher 统计仅筛选 SilentCipher 记录。混入 V3 会出现高于 0.68 的数字，不能拿来分析神经后端 presence policy。

### 历史负例 confidence

| 冻结阶段 | SilentCipher 无水印候选 | 最高候选 confidence | 被接受 |
|---|---:|---:|---:|
| P1 | 10 条候选 / 24 个 clean/MP3 条件 | 0.416667 | 0 |
| P3 | 10 条候选 | 0.392857 | 0 |
| P6 | 4 条候选 | 0.396825 | 0 |
| P8 | 15 条候选 / 36 个 WAV/ADTS/M4A 条件 | 0.448413 | 0 |

这些数据规模只适合工程检查，不是 FAR 估计。P8 的 `environment_04` AAC-M4A 消息候选为正确的 `D3916B24E8`，confidence 为 `0.638889`，被冻结阈值拒绝。P5 中 `speech_02` 的官方解析出现 `MISSING_TERMINATOR`；软解码诊断曾给出与预期字节相同的候选，但这不是官方解码成功，也没有取代 P4 解码器。

### 尚未确认的信道问题

P7 定位的是 P6 专用 ADTS 解码路径保留了 AAC-LC priming 帧的问题。P4 Studio 原有 AAC 使用 M4A，FFmpeg 根据容器 skip-sample 元数据处理起始 priming；P8 仅修正 Studio 自产文件的有效尾部样本范围，没有对任意外部文件固定裁掉 1,024 个样本。本轮 M4A 继续使用 AAC-LC 元数据路径，没有发现可复现的 P4/P8 信道缺陷。

## 3. 数据与冻结协议

清单在模型推理前冻结于 `configs/v4_p9_source_manifest.json`，SHA-256 为 `1bd887342b8f3c2415b79d7e756381b42a99823fe8552b20b7ddb9c352849276`。其中保留每个来源的 SHA-256、类别、采样率、时长、裁切位置、许可说明和来源页面；所有正负来源均按 SHA 排除 P1、P3、P5、P6 的既有文件。P7/P8 使用的是 P6 来源。

### 新音乐正例

六个上传文件经 FFprobe 核验为 Ogg/Vorbis，5 个为 44.1 kHz、1 个为 48 kHz；没有把 16 kHz 音频升采样后冒充原生高采样率音乐。它们是有损压缩音频文件，因此“原生高采样率”在本报告中仅指源文件本身的采样率元数据，不代表未压缩录音母带规格。

| 来源 ID | 音乐录音 | 源文件采样率 | 许可信息 |
|---|---|---:|---|
| `music_commons_01` | House Music Demo | 44.1 kHz | CC BY-SA 3.0；[Commons 页面](https://commons.wikimedia.org/wiki/File:House_Music_Demo.ogg) |
| `music_commons_02` | Maple Leaf Rag 录音 | 44.1 kHz | 录音 CC BY-SA 2.5；[Commons 页面](https://commons.wikimedia.org/wiki/File:Maple_Leaf_RagQ.ogg) |
| `music_commons_03` | Erik Satie - Gnossienne no. 1 | 44.1 kHz | 页面列有 CC BY-SA 与 GFDL 许可；[Commons 页面](https://commons.wikimedia.org/wiki/File:Erik_Satie_-_Gnossienne_no_1.ogg) |
| `music_commons_04` | Scott Joplin - Original Rags | 48 kHz | 演奏录音 CC BY-SA 3.0；[Commons 页面](https://commons.wikimedia.org/wiki/File:Scott_Joplin_-_Original_Rags_(1899).ogg) |
| `music_commons_05` | Minute Waltz，Sergej Rachmaninoff 演奏 | 44.1 kHz | 页面标注为美国境内公有领域录音；[Commons 页面](https://commons.wikimedia.org/wiki/File:Minute_Waltz,_by_Chopin_-_Performed_by_Sergej_Rachmaninoff.ogg) |
| `music_commons_06` | Pleasant Moments 钢琴卷录音 | 44.1 kHz | 页面标注为美国境内公有领域；[Commons 页面](https://commons.wikimedia.org/wiki/File:Pleasant_Moments_Piano_Roll.ogg) |

前四条为明确的 CC BY-SA/GFDL 来源；后两条的页面公有领域标记有美国司法辖区限定，本报告不将其表述为全球无条件公有领域。再发布前需另行核查适用地区许可。Commons 页面显示了文件许可与归属；实际测试文件采样率、SHA 和裁切点以冻结清单及本地 FFprobe 结果为准。

语音正例为 3 条新的 LibriVox 录音，环境声正例为 3 条新的 FreeSound 录音，均来自 MUSAN 已附的逐来源许可映射；本次使用的这些本地条目在其 LICENSE 文件中分别标为 Public Domain。MUSAN 汇总信息和数据许可可见 [OpenSLR MUSAN 页面](https://www.openslr.org/17/)，但具体素材许可仍以随数据附带的逐来源映射为准。语音和环境声输入源是 16 kHz，按冻结 DSP 预处理重采样到模型要求的 44.1 kHz；没有把它们计入高采样率音乐数量。

负例为 24 个未用于 P1–P8 的不同录音：8 首 FMA 音乐、8 条 LibriVox 语音、8 条 FreeSound 环境声；每类内为不同文件 ID/录音。它们均保留文件 SHA、许可出处和 12 秒裁切位置。负例素材不是 24 次同一文件的变换。

### 固定参数和信道

- 模型：Sony SilentCipher 官方 44.1 kHz / 40-bit `73999_iteration` 权重；默认 `message_sdr=47 dB`；`phase_shift_decoding=False`。
- 两条固定消息：`7B91D4E260`、`C3056AF18E`，均为 40-bit，每个正例来源各测试一次；不用于在线 detector 输入。
- 所有来源按清单固定位置裁切 12 秒，立体声先单声道混合，非 44.1 kHz 来源只重采样一次。
- 每条正例消息只嵌入一次并写成 PCM16 WAV；Clean、MP3、AAC 使用同一份标记 WAV。负例从未嵌入的对应 12 秒源片段生成。
- FFmpeg `6.1.1-3ubuntu5`：MP3 使用 `libmp3lame` CBR 128 kbps；AAC 使用 FFmpeg native AAC-LC 128 kbps，M4A 容器、单声道、44.1 kHz。解码后有效样本长度固定为 529,200。未使用 ADTS，也没有参考音频对齐或固定 priming 裁切。
- presence 阈值保持 `0.6805555373430252`；没有用本轮正负样本重新选阈值。

## 4. 来源级正例结果

每格为两条消息的“raw exact / correct accepted”；每类消息数为来源数的两倍，因此不代表独立来源数。

| 类别 | 独立来源 | Clean WAV | MP3 128k | AAC-LC / M4A 128k |
|---|---:|---:|---:|---:|
| Music | 6 | 12/12 / 12/12 | 12/12 / 12/12 | 12/12 / 11/12 |
| Speech | 3 | 6/6 / 6/6 | 6/6 / 6/6 | 6/6 / 6/6 |
| Environment | 3 | 6/6 / 6/6 | 6/6 / 6/6 | 6/6 / 6/6 |
| **全部** | **12** | **24/24 / 24/24** | **24/24 / 24/24** | **24/24 / 23/24** |

Clean 与 MP3 中，12/12 个来源的两条消息均精确恢复并被接受。AAC/M4A 中，12/12 个来源的两条消息均精确恢复；`music_commons_01` 的 `M2=C3056AF18E` 得分 0.674603，低于阈值，状态为 `UNKNOWN`。因此 11/12 个来源的两条消息均被接受，另 1 个来源为 1/2 正确接受。没有错误消息被接受，正例没有模型异常或 `DECODE_ERROR`。

### 负例结果

| 无水印条件 | 独立录音数 | `status=True` / 有候选 | 候选 confidence 范围（中位数） | `IDENTIFIED` | `DECODE_ERROR` |
|---|---:|---:|---:|---:|---:|
| Clean WAV | 24 | 9/24 | 0.361111–0.416667（0.376984） | 0/24 | 3/24 |
| MP3 128k | 24 | 4/24 | 0.369048–0.408730（0.378968） | 0/24 | 2/24 |
| AAC-LC / M4A 128k | 24 | 12/24 | 0.329365–0.400794（0.390873） | 0/24 | 0/24 |

其余负例返回 `UNKNOWN`。三个条件的最大负例候选 confidence 均低于冻结阈值；在这 24 个独立来源上，每种信道的错误接受均为 0。每个信道重复使用这 24 个录音，因此不可把 72 条 source-channel 记录说成 72 个独立负例，也不据此宣称正式 FAR。

## 5. 外部 M4A 文件边界盲检

用 `music_commons_01`、消息 `M1` 生成 AAC-LC/M4A 后，关闭编码写入阶段，再将保存的 `.m4a` 通过 Studio 正常的 `load_audio_file()` 文件读取路径加载；检测函数只接收该文件解码后的音频和冻结 detector。没有向 detector 传入原始音频、目标消息、原始样本数或嵌入会话。

文件读取接口读取到的容器采样率为 44.1 kHz，FFmpeg 将压缩文件解码为 48 kHz，预处理到模型要求的 44.1 kHz / 529,200 样本。盲检测候选为 `7B91D4E260`、confidence `0.706349`、状态 `IDENTIFIED`。期望消息仅在检测完成后用于离线评分，结果正确。这是一次独立文件读入边界验证，不是浏览器上传的视觉验收，也不是新增性能样本。

## 6. 音质与 CPU 资源

- 24 次模型嵌入 SNR：均值 `48.524 dB`，范围 `46.951–49.159 dB`。这是原始模型输入与嵌入输出的比较，不包含 MP3/AAC 失真。
- 模型加载：`0.039 s`；进程峰值 RSS：`1,458,548 KiB`（约 1.39 GiB）；CPU 线程数 4。
- 12 秒音频单次嵌入：均值 `3.631 s`，范围 `3.369–4.189 s`。
- 单次检测 wall time：clean 均值 `6.321 s`、MP3 `6.374 s`、AAC/M4A `6.327 s`；全部条件约 `5.83–7.53 s`。

这些是本机 CPU 单进程观察值，不是吞吐保证。峰值 RSS 是整个进程高水位，不是单次检测的增量内存。

## 7. 解码与 presence 的问题归属

1. **消息解码：** 本轮 12 个来源、两条消息、三种正例信道共 72 次正例检测中，raw exact 为 72/72，没有错误候选或正例解码异常。
2. **presence 判决：** AAC/M4A 有一条正确候选被拒绝。官方硬解码器给出正确 5-byte payload 且 `status=True`，但 confidence 低于政策阈值，故为 `UNKNOWN`。P8 的 `environment_04` 是同类历史例子（0.638889）。这属于阈值的保守漏检，不属于 M4A 文件解码失败。
3. **无水印负例：** 负例可产生候选且官方状态可能为真，但 P9 最大候选 confidence 为 0.416667，离阈值有间隔；presence policy 将所有负例留为 UNKNOWN 或解码错误，没有错误接受。
4. **信道处理：** Studio M4A 元数据处理路径在本次正常文件读入中工作。没有发现需要对 P4 AAC 路径追加固定偏移或修改 P8 尾部裁切规则的证据。

## 8. 决策与建议

`V4_P9_DECISION = BASELINE_RETAINED`

保留 SilentCipher 官方硬解码器、默认 47 dB 嵌入强度和 P1 冻结阈值，不改变 P4 Studio。P9 在新来源上的 Clean/MP3 接受为 24/24，AAC/M4A 接受为 23/24；三种信道的无水印负例均 0/24 接受，且正负候选分数在本轮样本中没有重叠。唯一可见弱点是 confidence policy 拒绝了一个正确 AAC 消息，加上 P8 的一个同类例子。现有证据不足以在不增加误接受风险的情况下选择新阈值，因此不下调阈值。

下一项有价值的工作应是**presence confidence 的独立校准**：预先分出开发来源来选择判决规则，再用全新、按来源留出的数据冻结验证漏检和错误接受。当前瓶颈在存在性置信度校准，而不是本轮的 message decoder、嵌入强度、M4A priming 或模型权重。24 个负例仍不足以支持正式总体 FAR；6 条音乐录音也不足以代表所有原生高采样率音乐。

## 9. 复现与工件

- 冻结来源和协议：`configs/v4_p9_source_manifest.json`
- 全量原始检测、confidence、codec 元数据、耗时、SNR、checkpoint hashes：`experiments/v4_p9/RESULTS.json`
- 隔离运行器：`scripts/v4_p9_detection_reliability.py`
- 本轮没有保存或提交原始音频、模型权重、绝对本机路径或凭证；正例下载、编解码临时文件在临时区清理。P0–P8 报告和结果、V3 与 Render 服务未修改。
