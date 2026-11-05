# V4-P3 SilentCipher 最终神经引擎门槛报告

**日期：2026-11-05**\
**判决：`V4_P3_ENGINE_DECISION = CONDITIONAL_GO`**

## 结论摘要

SilentCipher 在本轮 12 个 P1 不重合来源中，clean 与真实 MP3 128 kbps 条件各有 11/12 个来源能恢复两条固定消息；按重复消息记录为 22/24。唯一失败来源是一段语音：clean 两条都缺少终止符，MP3 一条产生错误候选，另一条仍缺少终止符。错误候选置信度低于 P1 冻结阈值，因此检测器判为 `UNKNOWN`，没有错误接受。

24 条无水印条件（12 个来源各 clean、MP3 两种负例）中，冻结 presence policy 接受数为 0。但样本规模只能支持工程判断，不能用于正式总体误报率声明。`decode_wav().status=True` 不能直接代表有水印：24 条负例有 10 条 status 为 True，其中 9 条给出合法五字节候选，另 1 条给出越界候选；均被独立 presence policy 拒绝。

SilentCipher 可以作为 **V4 主要神经候选/单 worker 演示后端**，但证据不足以让它成为无回退、适用于所有声音类别的唯一引擎。建议保留 V3 冻结 DSP 后端作为显式对照与回退；失败必须显示 `UNKNOWN`，不能隐藏。高采样率音乐泛化、正式误报率与权重公开再分发许可仍未得到证明。

```text
V4_P3_ENGINE_DECISION = CONDITIONAL_GO
SILENTCIPHER_AS_PRIMARY_NEURAL_CANDIDATE = YES, WITH EXPLICIT LIMITS AND V3 FALLBACK
SILENTCIPHER_AS_FINAL_SOLE_ENGINE = NOT YET
```

## 1. 冻结数据与协议

推理前冻结的[数据清单](../../../configs/v4_p3_source_manifest.json) SHA-256 为 `847f5a647c93bc896439c0ff5e38f701639b24c6c20af8611e118224a78ca56f`。清单含 12 个素材的相对路径、完整 SHA-256、采样率、时长、固定裁切偏移和许可。来源与 P1 不重合：音乐来自 MUSAN 的不同曲目，语音来自美国政府公共领域录音，环境声来自 SoundBible。

固定消息为 `D3916B24E8`、`2C6E94DB17`，种子 `20261105`。相同消息对用于每个来源；同源两条消息是重复测量，不是独立来源。输入为单声道、12 秒、44.1 kHz；源素材按统一流程重采样。MP3 用 FFmpeg `libmp3lame` CBR 128 kbps：PCM16 WAV 编码后解码为 float WAV。

**音乐采样率限制：**本机没有可用且与 P1 不重合的原生 44.1/48 kHz 音乐来源。六首音乐均来自 MUSAN 的 16 kHz 文件并重采样到 44.1 kHz。因此本轮能检查这些曲目的消息/压缩链路，但不能证明高频细节或原生高采样率音乐保真效果。没有将原始素材复制进仓库。

## 2. 按来源结果

`clean` 和 `MP3` 为两条消息中的完整精确恢复数；confidence 是有候选时的范围；`负例接受`为该来源两个无水印条件的接受数。完整 SHA-256 与许可文本见冻结清单。

| 来源 | 类别 / 固定裁切起点 | 源采样率 / 时长 | clean | MP3 128k | confidence clean / MP3 | 负例接受 |
|---|---|---:|---:|---:|---:|---:|
| music_01 | Jamendo `0000` / 123 s | 16 kHz / 471.849 s | 2/2 | 2/2 | .968–.980 / .964–.972 | 0/2 |
| music_02 | Jamendo `0037` / 45 s | 16 kHz / 206.001 s | 2/2 | 2/2 | .877–.897 / .865–.881 | 0/2 |
| music_03 | RFM `0000` / 60 s | 16 kHz / 171.984 s | 2/2 | 2/2 | .917–.937 / .893–.921 | 0/2 |
| music_04 | RFM `0058` / 70 s | 16 kHz / 120.529 s | 2/2 | 2/2 | .976–.984 / .972–.988 | 0/2 |
| music_05 | HD Classical `0000` / 100 s | 16 kHz / 207.961 s | 2/2 | 2/2 | .992–1.000 / .992–1.000 | 0/2 |
| music_06 | HD Classical `0039` / 130 s | 16 kHz / 187.063 s | 2/2 | 2/2 | 1.000 / 1.000 | 0/2 |
| speech_01 | US Government `0000` / 47 s | 16 kHz / 600.048 s | 2/2 | 2/2 | .817–.825 / .821–.829 | 0/2 |
| speech_02 | US Government `0007` / 200 s | 16 kHz / 599.980 s | **0/2** | **0/2** | — / .647 | 0/2 |
| speech_03 | US Government `0019` / 360 s | 16 kHz / 599.980 s | 2/2 | 2/2 | .984–.988 / .984–.988 | 0/2 |
| environment_01 | SoundBible Rain / 0 s | 16 kHz / 15.908 s | 2/2 | 2/2 | .845–.897 / .841–.893 | 0/2 |
| environment_02 | SoundBible Night Rain In Russian City / 13 s | 16 kHz / 62.642 s | 2/2 | 2/2 | .881–.889 / .869 | 0/2 |
| environment_03 | SoundBible Phone Ringing / 2 s | 16 kHz / 18.102 s | 2/2 | 2/2 | .913–.933 / .913 | 0/2 |

## 3. 恢复与存在性判决

阈值固定为 P1 开发集选择的 `0.6805555373430252`，P3 未重新拟合。presence 判决要求官方状态为真、存在合法五字节候选且 confidence 不低于阈值；否则为 `UNKNOWN`。`PRESENCE_CALIBRATION = PROVISIONAL`。

| 条件 | Exact message recovery | Correct accepted recovery | 错误消息接受 | 官方 status=True | 终止符缺失 |
|---|---:|---:|---:|---:|---:|
| 有水印 clean | 22/24 | 22/24 | 0 | 22/24 | 2/24 |
| 有水印 MP3 128k | 22/24 | 22/24 | 0 | 23/24 | 1/24 |
| 无水印 clean | — | — | 负例接受 0 | 5/12 | 未追踪全部负例帧 |
| 无水印 MP3 128k | — | — | 负例接受 0 | 5/12 | 未追踪全部负例帧 |

24 个负例条件中接受数为 0。clean 负例有 5 个合法候选；MP3 负例有 4 个合法候选，另有 1 个包含越界值的原始候选（`speech_02` MP3，confidence `.365`）。合法负例候选的最高 confidence 为 clean `.393`、MP3 `.389`，均低于阈值。clean 与 MP3 两个负例来自同源，不能视作 24 个独立来源或据此声明总体 FAR。

有水印候选 confidence 最低为 clean `.817`、MP3 `.647`；均值分别 `.932` 和 `.914`。MP3 最低值是错误候选而非正确恢复；presence 阈值拒绝了该候选，但 raw decoder 仍表现出预测退化。

按“官方 `status=False` 且无候选”计，有水印 clean 解码失败 2/24、有水印 MP3 解码失败 1/24；24 次 Python/model 调用均未抛出异常（`DECODE_ERROR` 0）。MP3 中另有一条官方 `status=True` 但消息错误的记录，属于错误解码而非拒绝或异常。

### speech_02 失败阶段

官方逐帧追踪显示，clean 的两条消息在 261 帧、12 组投票后均未检测到终止符，一致度分别约 `.659` 和 `.694`。这是**模型帧预测退化导致的终止符/消息解析失败**，不是阈值拒绝；没有发生 Python 异常或数值异常。

主实验的首次完整尝试在第 7 个来源的负例序列化时中止：日志器把官方的非五字节/越界消息候选直接转换为 bytes。修正日志器为仅接受合法五字节候选、保留原始异常符号并逐来源落盘后，使用相同冻结清单、消息、权重和信道完整重跑。该中止是实验记录器错误，不是 SilentCipher 推理错误；首次尝试未进入最终统计。

MP3 后，`D3916B24E8` 被解成错误消息 `D3916724E8`，confidence `.646825`，低于冻结阈值；`2C6E94DB17` 仍缺少终止符，逐帧一致度约 `.671`。该错误候选被判 `UNKNOWN`，未被接受。逐帧记录见[定向追踪结果](../../../experiments/v4_p3/SPEECH02_FAILURE_TRACE.json)。主实验第一次追踪时未将项目根目录放入导入路径，导致 trace 未写出；发现后对同一冻结输入/权重做四条件定向重放并补充记录。这个修正只影响诊断，不影响官方推理、模型参数或判决。

## 4. 音质与 CPU 资源

音质度量在重采样后的原音与模型输出之间对齐比较，未包含 MP3 编码损伤。LSD 为 4096 点 Hann 窗、2048 点 hop、幅度谱 log 差 RMS dB。

| 指标 | 结果 |
|---|---:|
| Embedding SNR | 均值 49.06 dB，中位数 48.97 dB，范围 48.52–50.43 dB（24 次嵌入） |
| Embedding LSD | 均值 2.82 dB，中位数 2.53 dB，范围 1.63–4.50 dB（24 次嵌入） |
| CPU 嵌入耗时 | 均值 3.34 s，中位数 3.33 s，范围 3.26–3.49 s（24 次嵌入） |
| CPU 检测耗时 | 均值 5.88 s，中位数 5.87 s，范围 5.76–6.15 s（72 次 decode） |
| 热缓存模型加载 | 0.044 s；不含 Python/Torch 导入，不代表冷启动总时延 |
| 峰值进程 RSS | 1,584,260 KiB，约 1.51 GiB；CPU 4 线程、单进程 |

SNR/LSD 不等价于主观听感。当前 CPU 足以运行单 worker 本地交互演示，但单段检测约六秒、峰值约 1.5 GiB；没有据此证明多并发或低延迟服务能力。P1 资源量级亦为数秒推理与约 1.58 GiB RSS。

## 5. 现有 GUI 回归

实际启动本机 Gradio 服务，通过 named endpoints 完成上传、嵌入、WAV/MP3 文件返回、独立上传和盲检。属于 API 驱动的真实服务回归；没有做浏览器视觉布局检查。

| 样本 | Clean 盲检 | MP3 往返与独立盲检 |
|---|---|---|
| P3 speech `speech_03` | `IDENTIFIED`，`D3916B24E8`，`.984127` | 往返完成；`IDENTIFIED` 同消息，`.980159` |
| P3 music `music_01` | `IDENTIFIED`，`D3916B24E8`，`.980159` | 往返完成；`IDENTIFIED` 同消息，`.984127` |
| P3 environment `environment_01` | `IDENTIFIED`，`D3916B24E8`，`.896825` | 往返完成；`IDENTIFIED` 同消息，`.888889` |
| P1 已知失败音乐 `music_03` | `IDENTIFIED`，`123456789A`，`.869048` | 往返完成；错误候选 `16C1DD0BB4`、`.345238`，判为 **`UNKNOWN`** |

四次均返回带水印 WAV、MP3 和解码 WAV。已知失败没有被演示流程改写成成功。停止服务后 GUI 临时存储目录和本轮临时输入文件均清理；视觉布局和浏览器行为未单独检查。

GUI 回调报告的嵌入 CPU 时间为 3.30–4.36 s，独立 clean/MP3 检测为 5.73–5.81 s；MP3 往返约 0.30–0.36 s。

## 6. P0/P1/P2 证据与 V3 边界

- **P0：**单段音乐 clean 与真实 MP3 128k 跑通，证明官方 CPU 推理可用；当时语音/环境与总体鲁棒性未验证，判为 `CONDITIONAL_GO`。
- **P1：**12 来源 clean 精确恢复 12/12、MP3 10/12，两条 MP3 失败都在同一音乐来源。官方 status 不能直接作为 presence 判决；P1 选出的阈值在本轮冻结沿用。
- **P2：**独立适配器与 Gradio MVP 可用；`music_03` MP3 产生错误候选并显示 `UNKNOWN`，主要问题是模型预测/终止符，不是阈值可调好。
- **P3：**新来源 clean 与 MP3 均为 11/12 来源完整恢复；失败转移到一段语音。多数来源跨类别表现良好，但来源相关失败仍存在。

本轮未重跑 V3。P1 的既有对照是 V3 6 秒/48 kHz/8-bit、MP3 exact 8/12；SilentCipher 是 12 秒/44.1 kHz/40-bit、P1 测试集 MP3 10/12。容量、时长、采样率与检测逻辑不同，不能直接排名。V3 算法、历史结果和 Render 服务保持冻结。

SilentCipher 官方源码为 MIT；P0/P1 没有找到官方 checkpoint 的独立许可声明。**源码 MIT 不自动证明权重可公开再分发。** 本轮复用既有权重，没有重下、修改或提交权重。若公开课程仓库，在澄清许可前不应打包 checkpoint。

P0/P1/P2 原报告、旧实验 JSON 和诊断文件的 SHA-256 在本轮前后保持不变；本轮仅新增 P3 文件，没有改 V3、Render 或官方权重，也未推送 GitHub。

## 7. 最终决策与课程系统建议

**SilentCipher 能否直接作为 V4 最终神经水印主引擎？**

它可作为主要神经候选和本地课程演示后端，但目前不够可靠到成为无回退的唯一主引擎。music/environment 的 MP3 结果有工程价值；P3 的语音来源级失败、错误候选和 provisional presence policy 仍构成明确限制。主要风险是**鲁棒性/盲检测校准**，其次是权重再分发许可未明确；本机 CPU 成本可接受单 worker 演示，音质信号级 SNR/LSD 没有显示明显资源性阻塞。

建议采用显式双后端课程系统：

1. 保留 V3 冻结 DSP 引擎作为可选对照/手动回退；不在检测失败时静默切换。
2. SilentCipher 作为神经演示路径，展示恢复消息、confidence 与 `IDENTIFIED / UNKNOWN / DECODE_ERROR`；对未知结果不显示检测成功。
3. 保持单模型实例、单 worker/排队和有限时长；共用明确的采样率/声道预处理、波形/频谱、MP3 信道、SNR/LSD 和试听流程。
4. 阈值继续标注 provisional；不要宣称正式 FAR、总体 SOTA 或与 V3 的公平性能排名。
5. 公开分发权重前确认许可；在此之前仅给出官方来源说明。

本轮未审查第二种模型：当前判决是 `CONDITIONAL_GO`，工程链路和多数来源已可用；主要限制仍是来源相关模型预测失败、临时阈值与 checkpoint 许可。若后续条件无法处理，再按单个替代模型做有界审查，不启动并行大规模复现。

本轮在引擎门槛判断结束，不启动后续实验或系统开发。

## 复现产物

- [数据清单](../../../configs/v4_p3_source_manifest.json)
- [主实验结果](../../../experiments/v4_p3/RESULTS.json)
- [speech_02 失败追踪](../../../experiments/v4_p3/SPEECH02_FAILURE_TRACE.json)
- [主实验脚本](../../../experiments/v4_p3/prototype/v4_p3_engine_gate.py)
- [失败追踪脚本](../../../experiments/v4_p3/prototype/v4_p3_trace_failed_source.py)
