# V4-P1 SilentCipher 独立验证与主引擎选型报告

**日期：2026-11-04**\
**判决：`V4_P1_DECISION = CONDITIONAL_GO`**\
**选择：`SilentCipher` 可作为 V4 神经水印主候选；现阶段不应作为唯一引擎或冻结为无条件正式主引擎。保留 V3 冻结 DSP 路径。**

## 结论摘要

12 个独立来源（语音、音乐、环境声各 4 个）完成了官方 44.1 kHz 权重的 40-bit clean、MP3 128 kbps 及无水印正负例；V3 使用同源切片、冻结的 6 秒/48 kHz/8-bit 公共 API 做了配对对照。两条固定消息不是独立来源，统计单位仍是来源。

在保留测试集上，SilentCipher clean 精确恢复 12/12，MP3 精确恢复 10/12；两条 MP3 失败都来自同一条音乐来源。只看 `decode_wav().status` 会把 10/24 条无水印负例误当成有候选消息。开发集选择的探索性 confidence 阈值为 0.68056；冻结后测试集 clean 接受 12/12、MP3 接受 10/12，12 个负例条件均拒绝。负例仅来自 6 个独立测试来源，不能据此宣称正式误报率。

SilentCipher 的平均嵌入 SNR 为 48.91 dB，平均 log-spectral distortion（LSD）为 2.44 dB。CPU 平均每次嵌入 4.38 s、盲检测 7.68 s；本进程峰值 RSS 约 1.58 GiB。V3 在本轮测试集的 MP3 精确恢复为 8/12，clean 为 12/12；检测约 0.021 s，单独代表性进程峰值 RSS 约 140.5 MiB。V3 与 SilentCipher 的消息容量、音长、采样率及实现不同，因此这组小样本只能作为工程参照，不能据成功率直接排名。

轻量裁剪检查仅用一条测试语音：去掉开头 0.5 秒后普通检测恢复了正确消息，但 confidence 0.671 低于本轮阈值；官方 phase-shift 搜索耗到 90 秒限制仍返回无消息。9 秒短片段普通检测也失败。当前没有证据支持把裁剪鲁棒性作为 SilentCipher 的已验证能力。

## 1. 范围、冻结状态与模型身份

- V4 独立工作区基线仍为 `research/v4-p0 @ 042ce9eaa841c6bd126a3daefcdc8ff14aebdf1c`。原 P0 三个交付文件 SHA-256 保持不变；新增 P1 内容只写入 V4-P1 路径。
- V3 冻结工作区仍为 `7fe678234e8af1d0be34a0a3e56297c7182945ff`，工作区干净。本轮调用其 `app.v3_api` 公共嵌入/盲检测接口；未修改 V3 算法、历史实验或 Render 服务，也未推送 GitHub。
- SilentCipher 官方仓库审查版本为 `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10`，模型为官方 44.1 kHz `73999_iteration`。权重未重新下载；三个使用中的 checkpoint SHA-256 与 P0 一致，列在 `experiments/v4_p1/RESULTS.json`。
- 官方仓库源码许可证为 MIT；官方发布的模型归档没有随附独立权重许可声明。源码许可不自动证明权重可再分发，公开分发模型前仍须澄清权重条款。
- 已验证环境为 Python 3.12.14、PyTorch 2.14.0 CPU、librosa 0.10.2.post1、soundfile 0.13.1、FFmpeg 6.1.1；没有 GPU、训练或新大型依赖。该 PyTorch 版本推理实测可运行，但高于官方 requirements 中的 `torch<=2.0.0` 上限，因此属于工程可运行而非上游声明的依赖组合。

## 2. 数据与协议冻结

清单在模型运行前冻结于 `configs/v4_p1_source_manifest.json`。来源切片使用固定随机种子 `20261104` 生成并保存起始偏移。每类 2 个开发来源、2 个保留测试来源；来源文件/录音组不重复。文件 SHA-256、源采样率、源时长、切片偏移、许可和来源页均在清单中。清单使用相对文件名和环境变量标识外部数据根目录，没有复制音频到仓库。

消息在运行前固定为 SilentCipher 消息 A `[18, 52, 86, 120, 154]`、消息 B `[237, 203, 169, 135, 101]`（每条 40 bit）；V3 使用各自首字节 `0x12` 与 `0xED` 作为 8-bit payload。每个来源的两条消息是重复测量，不计作两个独立样本。

SilentCipher 每次输入单声道、44.1 kHz、12.0 秒。语音和环境音源文件为 16 kHz，按固定切片重采样到模型采样率；音乐源来自原生 44.1/48 kHz FMA 音轨，不用 16 kHz 升采样音乐代表高保真音乐。音乐文件本身是 FMA 的 MP3 发行文件，所以“clean”指其解码后的源片段，并非无损母带。V3 使用相同 12 秒源切片的前 6 秒，固定 48 kHz/6 秒/8-bit public API；协议采用 V3 冻结的 REAL_TOP32、strength 1.60 与既有 presence threshold。

攻击使用 FFmpeg `libmp3lame` 单声道 CBR 128 kbps：将嵌入后的 12 秒音频编码为 MP3，再解码为 PCM float 后盲检测；负例将未嵌入源片段走同一往返链路。每个来源执行 2 条消息的 clean 与 MP3 正例，以及 clean 原始负例和 MP3 负例。SilentCipher 与 V3 各产生 72 条检测记录，共 144 条。

### 12 个固定来源

| ID | 类别 / 划分 | 来源与文件 | 源采样率 | 源时长 / 片段时长 | 切片起点 | 文件 SHA-256 |
|---|---|---|---:|---:|---:|---|
| speech_01 | 语音 / 开发 | MUSAN LibriVox `speech-librivox-0084.wav` | 16 kHz | 391.314 / 12 s | 280.954 s | `53d6fd8c3ddde750f8d664a9bb5c265bfc5f1d112ee207337709b54f910bde3f` |
| speech_02 | 语音 / 开发 | MUSAN LibriVox `speech-librivox-0085.wav` | 16 kHz | 593.189 / 12 s | 121.495 s | `7cac6ee672edc1e7bf105204afffa52aa8fc326a052ae796b28178542d441ff6` |
| speech_03 | 语音 / 保留测试 | MUSAN LibriVox `speech-librivox-0094.wav` | 16 kHz | 176.536 / 12 s | 61.012 s | `b529147404ffd239df9a5eaddfe19e7130393fb756e4f56f4ee85d68cd63cc7d` |
| speech_04 | 语音 / 保留测试 | MUSAN LibriVox `speech-librivox-0095.wav` | 16 kHz | 548.075 / 12 s | 317.001 s | `9501841a7d838ef25caabdb474c0b25a39287960a795e738e763da3460bab370` |
| music_01 | 音乐 / 开发 | Maarten Schellekens, “Sax and Piano (free track)” | 44.1 kHz | 94.201 / 12 s | 18.745 s | `83b8c88b10bbb21788636bccca8f0aa6817d195ef91557507d0981f323865ff1` |
| music_02 | 音乐 / 开发 | Monplaisir, “Free To Use 1” | 44.1 kHz | 192.026 / 12 s | 1.173 s | `44c5a2df842e3dcee420e391a39170e5f94e62d1031521c8851bc796917b4a12` |
| music_03 | 音乐 / 保留测试 | Beat Mekanik, “Dreams (Free Stems)” | 44.1 kHz | 237.923 / 12 s | 194.608 s | `5f46ae433685dcab0b86209e3fad47b235880780db2cbb23e39a5ee86a5274a3` |
| music_04 | 音乐 / 保留测试 | Play House, “Random Drop” | 48 kHz | 169.836 / 12 s | 92.500 s | `25275747a5c5535944e7dce26b3b6b21cb80263215717c0b08185b4381f30ff8` |
| environment_01 | 环境声 / 开发 | MUSAN FreeSound `noise-free-sound-0121.wav` | 16 kHz | 44.000 / 12 s | 30.000 s | `7311ae6a69bced04e53a8f07201a9951e2c5e56b026afc3d38ef69c4d8d2b7e5` |
| environment_02 | 环境声 / 开发 | MUSAN FreeSound `noise-free-sound-0130.wav` | 16 kHz | 38.870 / 12 s | 18.623 s | `ec7f593b49029f41c26a4c40561e15471f80137355f1b3ba190ef732e372a431` |
| environment_03 | 环境声 / 保留测试 | MUSAN FreeSound `noise-free-sound-0141.wav` | 16 kHz | 135.072 / 12 s | 9.063 s | `92f917eba755c555472d7588a981578c9b8a0f7b78b5e085fbbc53095fb09fa5` |
| environment_04 | 环境声 / 保留测试 | MUSAN FreeSound `noise-free-sound-0142.wav` | 16 kHz | 38.9998 / 12 s | 10.142 s | `5822d43e5858dae030a1fbaa6afab9c6d8f34e39f6c3153c2956736e5ae39ccc` |

语音来源在对应 MUSAN 清单中标为 Public Domain；环境声使用 MUSAN FreeSound 清单中标为 Public Domain 的条目。MUSAN 数据集总体许可为 CC BY 4.0。4 首音乐逐曲页面显示 CC0；未假定 FMA 整个平台共享同一许可。

## 3. 检测语义与开发集阈值

官方 `decode_wav()` 不需要原始音频，可独立盲解码。源码在每个声道/消息上尝试还原消息；运行无异常会返回 `status=True`、消息候选和 `confidences`。`confidence` 是帧间一致度，不是官方校准的水印存在概率。无水印音频可能生成看似有效的 5-byte 候选，只有解析失败才令 `status=False`。因此 `status=True` 不能解释为水印存在。

本轮只为探索是否可建立 presence 判决，在开发集利用 confidence 的已知正/负标签选择阈值，不用消息内容或文件名决定 presence。开发集 24 条正例的最小 confidence 为 0.944444；12 条负例中最大候选 confidence 为 0.416667。冻结阈值取两者中点 `0.680556`。开发集得到 24/24 正例接受、12/12 负例拒绝；这只是小开发集的阈值校准结果。

保留测试集按该冻结阈值：clean 正例 12/12 接受且消息正确；MP3 正例 10/12 接受且消息正确；raw 负例 0/6 接受；MP3 负例 0/6 接受。测试集无水印的 12 个“来源 × 信道”条件来自 6 个独立来源，样本太少，不报告正式 FAR。仅看原始 `status`，测试 raw 负例有 3/6、MP3 负例有 4/6 返回消息候选；开发集另有 raw 2/6、MP3 1/6。所有这些候选的 confidence 低于冻结阈值。本轮正例中，已被 presence 判决接受的消息均正确；错误消息接受为 0。

### 每个来源的恢复与负例候选

正例列为精确恢复数/两条消息。负例列为原始 `status=True` 候选数/一个负例；括号中是冻结阈值接受数。V3 无水印判决直接采用冻结公共 API 状态。

| 来源 | SilentCipher clean | SilentCipher MP3 | SC raw 负例候选（接受） | SC MP3 负例候选（接受） | V3 clean | V3 MP3 | V3 raw / MP3 负例 `IDENTIFIED` |
|---|---:|---:|---:|---:|---:|---:|---:|
| speech_01 | 2/2 | 2/2 | 0/1 (0) | 0/1 (0) | 2/2 | 2/2 | 0 / 0 |
| speech_02 | 2/2 | 2/2 | 1/1 (0) | 1/1 (0) | 2/2 | 2/2 | 0 / 0 |
| speech_03 | 2/2 | 2/2 | 1/1 (0) | 1/1 (0) | 2/2 | 2/2 | 0 / 0 |
| speech_04 | 2/2 | 2/2 | 0/1 (0) | 1/1 (0) | 2/2 | 1/2 | 0 / 0 |
| music_01 | 2/2 | 2/2 | 1/1 (0) | 0/1 (0) | 2/2 | 0/2 | 0 / 0 |
| music_02 | 2/2 | 2/2 | 0/1 (0) | 0/1 (0) | 2/2 | 2/2 | 0 / 0 |
| music_03 | 2/2 | 0/2 | 1/1 (0) | 0/1 (0) | 2/2 | 0/2 | 0 / 0 |
| music_04 | 2/2 | 2/2 | 0/1 (0) | 0/1 (0) | 2/2 | 1/2 | 0 / 0 |
| environment_01 | 2/2 | 2/2 | 0/1 (0) | 0/1 (0) | 2/2 | 2/2 | 0 / 0 |
| environment_02 | 2/2 | 2/2 | 0/1 (0) | 0/1 (0) | 2/2 | 2/2 | 0 / 0 |
| environment_03 | 2/2 | 2/2 | 0/1 (0) | 1/1 (0) | 2/2 | 2/2 | 0 / 0 |
| environment_04 | 2/2 | 2/2 | 1/1 (0) | 1/1 (0) | 2/2 | 2/2 | 0 / 0 |

“无水印候选”不等于真水印或接受结果；它展示了直接把 `status=True` 用作存在判决会产生的误接收。`music_03` 的两条 MP3 正例均返回 `status=False` / `Could not find message`，没有 confidence；其余测试正例成功时均精确解码。

## 4. 音质、资源与 V3 对照

嵌入音质测量均在 MP3 攻击前，使用相同定义：`SNR=10log10(sum(x²)/sum((x-y)²))`；LSD 为 4096 点 Hann 窗、2048 hop 的 STFT 幅度 log 比差 RMS（dB）。SilentCipher 使用 12 秒，V3 使用其 6 秒输入；数值不能消除音长/模型差异，也不替代听音测试。

| 引擎 / 集合 | Exact clean | Exact MP3 128k | 嵌入 SNR 均值 | LSD 均值 | CPU 嵌入均值 | CPU 检测均值 |
|---|---:|---:|---:|---:|---:|---:|
| SilentCipher / 开发 | 12/12 | 12/12 | 48.61 dB | 2.76 dB | 4.35 s | 7.66 s |
| SilentCipher / 保留测试 | 12/12 | 10/12 | 49.21 dB | 2.12 dB | 4.42 s | 7.70 s |
| SilentCipher / 全部 | 24/24 | 22/24 | 48.91 dB | 2.44 dB | 4.38 s | 7.68 s |
| V3 / 开发 | 12/12 | 10/12 | 53.74 dB | 7.82 dB | 0.056 s | 0.021 s |
| V3 / 保留测试 | 12/12 | 8/12 | 53.44 dB | 7.37 dB | 0.064 s | 0.021 s |
| V3 / 全部 | 24/24 | 18/24 | 53.59 dB | 7.59 dB | 0.060 s | 0.021 s |

各测试类别的正例精确恢复：SilentCipher clean 的语音/音乐/环境声分别 4/4、4/4、4/4；MP3 分别 4/4、2/4、4/4。V3 clean 分别 4/4、4/4、4/4；MP3 分别 3/4、1/4、4/4。音乐测试来源只有两个，表现差异很大，不能把此结果当成音乐总体结论。

SilentCipher 全部 24 次嵌入 SNR 范围为 47.97–50.50 dB，LSD 为 0.59–3.50 dB；V3 SNR 范围为 42.41–63.07 dB，LSD 为 2.62–12.40 dB。SNR 与 LSD 两个指标对修改分布的响应不同，本轮没有主观 ABX 听音，不能仅凭平均指标宣称哪种更好听。

SilentCipher warm-cache 模型加载计时 0.039 s（不含 Python/Torch 进程启动）；峰值 RSS 为 1,651,296 KiB，约 1.58 GiB。V3 独立单来源代表性进程峰值 RSS 为 143,876 KiB，约 140.5 MiB；全样本运行测得的 V3 平均耗时如表。SilentCipher 无 GPU 也能执行，但单请求数秒级检测和约 1.6 GiB 峰值意味着课程演示需单模型实例、单 worker/队列和并发限制，不适合直接承诺低延迟并发服务。

### 不可直接排名的原因

- SilentCipher 名义消息为 40 bit/12 秒/44.1 kHz，V3 为 8 bit/6 秒/48 kHz；容量和时长都不同。
- 两者均处理相同来源，但 SilentCipher 与 V3 的嵌入机制、消息编码、输入长度与预处理协议不同。
- 测试来源只有 6 个，类别内仅 2 个；一条音乐来源即可造成 2 个 MP3 失败。
- V3 测试负例都得到 `UNKNOWN`，SilentCipher 则必须额外校准 confidence 才能形成 presence 判决；两者状态语义不相同。
- SNR/LSD 是工程客观指标，不等于感知音质或用户盲听结论。

## 5. 轻量裁剪检查

仅测试 `speech_03` 的消息 A，使用同一条 SilentCipher 12 秒水印信号；没有扩展到其他来源。

| 输入 | ordinary decode | phase-shift decode | 观察 |
|---|---|---|---|
| 去除开头 0.5 秒，剩余 11.5 秒 | 6.36 s；`status=True`；消息 A 正确；confidence 0.6710 | 90.15 s 后无消息，官方函数返回 `status=False`, `Could not find message` | ordinary 恢复成功但低于本轮 presence 阈值 0.68056；phase-shift 搜索触及 90 秒硬预算 |
| 从 1 秒处取 9 秒短片段 | 4.45 s；`status=False`, `Could not find message` | 未运行 | 第一项 phase-shift 已触及预算，按界限停止扩展 |

官方 `get_best_ps()` 会以 10 个样点步长扫描整个 2048-sample STFT hop；此项裁剪检查证明它在 CPU 上可能成为分钟级瓶颈。本轮不能声称 SilentCipher 已具备可用的裁剪鲁棒性。裁剪的原始记录见 `experiments/v4_p1/CROP_CHECK.json`。

## 6. 官方模型审查与证据边界

- **机制和容量（SOURCE VERIFIED）：**44.1 kHz 配置使用 `N_FFT=4096`、`HOP_LENGTH=2048`、消息维度 5、消息长度 21；5 个字节拆为 20 个 2-bit 符号加终止标记并按时频帧重复。单声道一次 40 bit；官方支持按声道处理多声道，但本轮只测单声道。 编码端以 STFT 幅度载波和消息表示产生受限谱扰动，再以原载波相位逆变换成波形；解码端从接收音频的 STFT 幅度逐帧还原消息符号。
- **盲检测（SOURCE VERIFIED + RUNTIME PASS）：**`decode_wav(watermarked_or_received, sr, phase_shift_decoding=...)` 不需要原音频。本轮 12 个真实来源运行 clean、MP3、负例均成功返回或记录异常。真正独立盲解码不等于存在性检测，本轮证明原始 status 有大量负例候选。
- **压缩（SOURCE VERIFIED / LIMITED RUNTIME PASS）：**配置包含 MP3/AAC 等训练增强；本轮实测仅 FFmpeg MP3 128 kbps。没有测试 AAC、重采样攻击、剪辑、混响或社交平台转码。
- **裁剪（LIMITED RUNTIME PASS / BOTTLENECK）：**README 提供 `phase_shift_decoding=True`；本轮一次 0.5 秒裁剪搜索到达 90 秒预算且没有消息，短裁剪未用 phase 搜索。
- **兼容性（RUNTIME PASS, UPSTREAM VERSION RANGE NOT VERIFIED）：**CPU 执行成功；当前依赖组合高于上游 PyTorch 声明上限。需要在课程项目环境锁定可重复版本。
- **许可（PARTIAL SOURCE VERIFIED）：**官方代码 MIT；官方权重许可未独立明确。不得据代码许可证推断权重可公开再分发。

## 7. 风险与选型

### 能支持的判断

1. 官方 44.1 kHz 权重可以在现有 CPU 上真实运行，完成 40-bit 嵌入、独立盲解码及 MP3 128 kbps 往返。真实语音、音乐和环境声 clean 全部精确恢复；保留集 MP3 为 10/12。
2. 在本轮小数据中，confidence 对正负样本形成了较大的开发集间隔；用 dev-only 阈值后保留集负例均拒绝。`status=True` 本身不能作为 presence 判定。
3. SilentCipher 是比从零训练更适合继续做 V4 主神经引擎验证的候选：40-bit/12 秒能力在本轮确实出现，MP3 测试数值高于本轮同源 V3 对照，但并没有超出小样本所能支持的范围。

### 尚不能支持的判断

- 不能宣称 MP3 128 kbps 的泛化成功率达到某个总体百分比；音乐保留测试只有两首，其中一首两条消息均失败。
- 不能宣称正式误报率为 0；测试只有 6 个独立负例来源，且直接 `status=True` 在 10/24 无水印条件生成了候选。
- 不能宣称裁剪鲁棒；presence 阈值拒绝了 confidence 0.671 的正确偏移恢复，phase search 触及 90 秒限制。
- 不能宣称感知音质优于 V3；没有听音实验，SNR/LSD 也不能代替感知评价。
- 不能承诺交互式低延迟或高并发；当前 CPU 检测约 7.7 秒/请求、RSS 约 1.58 GiB。
- 不能公开分发官方 checkpoint，直到权重许可边界得到确认；也尚未证明上游声明的 Torch<=2.0 环境组合可运行。

## 8. 最终决定与后续课程设计建议

```text
V4_P1_DECISION = CONDITIONAL_GO
SILENTCIPHER_AS_V4_NEURAL_PRIMARY = CONDITIONAL_GO
SILENTCIPHER_AS_ONLY_ENGINE = NO
V3_FROZEN_DSP_COMPARATOR_AND_FALLBACK = RETAIN
```

**SilentCipher 能否作为最终 V4 的主要算法？**可以有条件地作为主要神经水印引擎候选，但应与 V3 冻结 DSP 引擎并存，当前不能作为唯一后端或不带阈值的正式主引擎。阻碍因素首要是盲检测的 presence 校准和裁剪搜索资源成本，其次是音乐 MP3 小样本不稳定、CPU 每请求代价及模型权重许可待确认。嵌入音质没有显示明显工程阻断，但本轮没有主观听音验证。

建议后续课程系统采用双后端适配层：SilentCipher 负责高容量 40-bit/12 秒神经路径，V3 继续承担轻量 DSP 基线/回退；共用明确的采样率与声道预处理、MP3/AAC 信道、原音/水印试听、波形/频谱、SNR/LSD 分析和盲检测界面。presence 作为独立于解码的校准决策输出，同时展示 confidence 和拒绝状态；phase-shift crop 搜索不应默认同步执行，应有任务队列与时限。下一轮最值得验证的是增加独立音乐/负例来源、冻结分层 presence 阈值并做外部测试，确认误报控制、音乐 MP3 失败模式、裁剪搜索时间及 checkpoint 许可，再决定是否冻结为正式主引擎。

## 9. 实验文件与外部来源

- 原始来源、消息、偏移、哈希和许可清单：`configs/v4_p1_source_manifest.json`
- 每条原始检测与性能记录：`experiments/v4_p1/RESULTS.json`、`experiments/v4_p1/RESULTS.csv`
- 裁剪记录：`experiments/v4_p1/CROP_CHECK.json`
- 最小 CPU 复现脚本：`scripts/v4_p1_validate.py`
- P0 冻结报告：`V4_P0_FEASIBILITY_REPORT.md`

官方与数据来源：

- [Sony SilentCipher 官方仓库与 README](https://github.com/sony/silentcipher)
- [SilentCipher 官方 44.1 kHz 推理源码（审查提交）](https://github.com/sony/silentcipher/blob/c11afe0e2df73f1ac0f848e2903b8af36e6a0b10/src/silentcipher/server.py)
- [官方依赖声明](https://github.com/sony/silentcipher/blob/master/requirements.txt)
- [官方模型发布页](https://github.com/sony/silentcipher/releases/tag/release)
- [官方仓库 MIT 许可证](https://github.com/sony/silentcipher/blob/master/LICENSE)
- [MUSAN / OpenSLR 17](https://www.openslr.org/17/)
- FMA 单曲许可页：[Sax and Piano](https://freemusicarchive.org/music/maarten-schellekens/public-domain-1/sax-and-piano-free-track/)、[Free To Use 1](https://freemusicarchive.org/music/Monplaisir/Free_To_Use/Monplaisir_-_Free_To_Use_-_01_Free_To_Use_1/)、[Dreams (Free Stems)](https://freemusicarchive.org/music/beat-mekanik/single/dreams-free-stems/)、[Random Drop](https://freemusicarchive.org/music/play-house/single/random-drop/)。
