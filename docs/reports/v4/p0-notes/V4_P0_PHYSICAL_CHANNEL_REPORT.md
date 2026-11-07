# V4-P0 物理通道与失败机制报告

## 1. 冻结 V3 对照

V3 8-bit Soft-Code 没有被修改。对照使用：48 kHz、6 秒、REAL_TOP32、32 个
物理 B1 位、每位 4 次非重叠 2048-sample frame、`strength=1.60`、8-bit
capacity code、presence threshold `0.7855073980199624`。

V3 的上游物理通道仍然是每个 carrier A/B 两侧的 log-magnitude 差，经过固定
二元格点量化；检测只读取接收音频和公开 selector。历史合成通道审计已经显示，
speech/environment 的 MP3 后差值漂移明显高于 music，重复统计量也不总是独立。
本报告不修改或重解释那些冻结结果。

## 2. V4-TF-SS 候选

本轮新候选真正改变了通道：Hann-window、`n_fft=2048`、`hop=512` 的中心 padding
STFT；每一帧用 seed `20261025` 生成 1.5--12 kHz 内 96 个平衡正负载波；payload
bit 在所有时间帧中循环分配；在 log-magnitude 域按局部能量产生有限 salience
权重；接收端重建相同 STFT 并用 signed correlation 聚合。检测器没有 clean audio、
消息或嵌入端搜索记录。

未嵌入的 STFT round-trip regression 误差小于 `1e-10`，说明候选的分析/合成基础
路径满足数值重构要求；这不等价于修改后频谱与检测频谱完全一致。

## 3. 真实 development-only 结果

数据为历史 V3 development split 中每类 3 个 MUSAN source，共 9 个来源；每个
来源使用两个固定消息。它们曾参与历史开发，故不能叫 V4 独立测试集。

| 方法 | 条件 | exact recovery | logical BER | mean SNR | mean LSD | accepted |
|---|---|---:|---:|---:|---:|---:|
| V3 8-bit Soft-Code | clean | 18/18 | 0.0000 | 56.69 dB | 0.0296 dB | 18/18 |
| V3 8-bit Soft-Code | MP3 128k | 18/18 | 0.0000 | 56.69 dB | 0.0296 dB | 18/18 |
| V4-TF 8-bit | clean | 0/36 | 0.4861 | 53.72 dB | 0.2798 dB | 36/36 |
| V4-TF 8-bit | MP3 128k | 0/36 | 0.4965 | 53.72 dB | 0.2798 dB | 36/36 |
| V4-TF 16-bit | clean | 0/36 | 0.4236 | 53.78 dB | 0.2920 dB | 36/36 |
| V4-TF 16-bit | MP3 128k | 0/36 | 0.4514 | 53.78 dB | 0.2920 dB | 36/36 |

V4 的初始 rejector threshold 为 `0.02`，不是从测试集校准。对于 8/16-bit：

- clean negative false positive：18/18；
- clean-MP3 negative false positive：18/18；
- 因而当前 threshold 没有形成 presence 与 message decoding 的可用分离。

V3 development negative 仅作对照：clean FPR 1/9、MP3-clean FPR 0/9；样本太少，
不能宣称低于 1% FPR。

## 4. 逐 bit 诊断示例

在一个 speech development source、V4 8-bit、strength `0.04` 上，四种输入的
bit statistic 如下。`clean_host` 是未嵌入原音频，`marked` 是嵌入后，后两列是
真实 MP3 往返结果。

| input | recovered | presence score | signed per-bit statistic |
|---|---|---:|---|
| clean_host | `10001101` | 0.32454 | `0.355,-0.455,-0.473,-0.179,0.051,0.530,-0.313,0.241` |
| marked | `10000101` | 0.29376 | `0.428,-0.529,-0.399,-0.106,-0.022,0.458,-0.240,0.168` |
| marked_mp3 | `10001101` | 0.36109 | `0.508,-0.645,-0.487,-0.145,0.018,0.507,-0.326,0.253` |
| clean_mp3 | `10001101` | 0.39268 | `0.449,-0.560,-0.574,-0.166,0.071,0.571,-0.438,0.311` |

这说明当前失败首先发生在 clean host 干扰和 overlap-add 后的频谱一致性上：
marked statistic 没有稳定脱离 clean statistic，clean MP3 甚至产生同量级或更高的
presence score。MP3 不是唯一失败源；在没有 codec 的 clean 条件下已经无法盲解码。

## 5. 机制结论

本轮证据支持的有限结论是：

1. 简单的多时频载波和 received-side 局部能量权重，未能在真实音频上压过 host
   correlation；
2. 通过 overlap-add 修改连续 STFT frame 后，重新分析得到的 detector statistic
   不等于嵌入时指定的 spectrum statistic；
3. 低于 V3 的约 3 dB SNR 和约 9 倍 LSD 并没有换来任何有效消息恢复；
4. 当前 rejector 仅有接口，不是可用的 presence detector；
5. 不应通过提高 strength、改阈值或在这些来源上继续搜索来掩盖失败。
