# V3-P0-R1 真实音频与配对信道报告

状态：`R1_STATUS = PARTIAL`

本报告记录的是本地可复现的 R1 证据，不是论文指标复述，也不是对 Course V2 任意
32-bit 消息恢复能力的重新声明。冻结的 B1/REAL_TOP32 实现没有被修改。

## 1. 数据与 provenance

实验使用冻结 manifest：
`configs/v3_p0_r1_real_audio_manifest.json`。

| 项目 | 结果 |
|---|---|
| 数据来源 | 本机 `/home/nsk/datasets/MUSAN`，OpenSLR SLR17 元数据来源 |
| manifest 状态 | `FROZEN` |
| 独立 source recordings | 60 |
| Speech / Music / Environment | 各 20 |
| 每类 dev / test | 10 / 10 |
| split 单位 | 原始来源文件；FMA 音乐按较高层级 license group 分组 |
| 原始采样率 / 声道 | 16 kHz / mono，60 条均如此 |
| 原始容器 | WAV |
| 最短原始时长 | 6.0005625 s |
| manifest SHA256 | `2f9919e0e635f91cc9741c858f9c0bb235095215729ba5b555546d2ffb17ad62` |
| 仓库是否包含原始音频 | 否，仅保存 metadata、SHA256 和统计结果 |

数据集父级引用为 [OpenSLR SLR17 MUSAN](https://www.openslr.org/17/)，其公开列表标注
CC BY 4.0；本地 manifest 同时保留了 LibriVox、FreeSound 和 FMA 的逐源或子库许可
说明。音乐条目的许可并不统一，不能将全部源文件笼统视为 MIT 或统一 CC BY。

manifest 排除了两个已审计 Course V2 manifest 中列出的路径。`historical_use_status`
只表示“未列入这两个 manifest”，不能证明这些文件在所有历史实验中从未被读取；该
范围外的历史使用情况仍属于 provenance limitation。

## 2. 固定实验协议

- 所有源文件先按项目公开系统相同的 polyphase 规则从 16 kHz 重采样到 48 kHz，取
  每个源的前 6 秒；不足部分补零。不做额外峰值归一化。
- 每个 source recording 使用两个预先固定的 8-bit 消息，消息生成 seed 为 7 和 23。
  两条消息是同一 source 上的 paired trials，不计作两个独立录音。
- 冻结 B1 使用 `REAL_TOP32`、strength `1.28`、4 repetitions/physical bit。
  为匹配 8-bit 有效容量，将每个逻辑位固定重复到四个物理位；报告中的 B1 数字是
  “8-bit logical wrapper”，不是任意 32-bit 消息恢复率。
- 候选方法为 P0 已有 keyed local-normalized soft-correlation 原型，strength 固定
  为 P0 开发点 `0.02`、seed `23`、8 bits、16 repetitions/bit。R1 未用 test 选择
  strength。
- MP3 使用本机 FFmpeg 6.1.1、`libmp3lame`、128 kbps，真实 encode/decode。
- 只在 dev split 校准 presence threshold；test split 不重新调阈值。

## 3. 独立 test 结果

下面 BER 和 exact recovery 的统计单位是两个 message trials/source；同时保留 source-level
“两个消息均成功”的结果，避免把重复消息误算成独立录音。

### 3.1 MP3 128 kbps

| 方法 | 类别 | logical trials | BER | exact recovery | 两消息均成功的 source |
|---|---:|---:|---:|---:|---:|
| B1 8-bit wrapper | Speech | 20 | 0.01875 | 17/20 (85.0%) | 7/10 |
| B1 8-bit wrapper | Music | 20 | 0.02500 | 16/20 (80.0%) | 6/10 |
| B1 8-bit wrapper | Environment | 20 | 0.05625 | 16/20 (80.0%) | 7/10 |
| Candidate | Speech | 20 | 0.05000 | 13/20 (65.0%) | 6/10 |
| Candidate | Music | 20 | 0.06875 | 11/20 (55.0%) | 4/10 |
| Candidate | Environment | 20 | 0.04375 | 15/20 (75.0%) | 6/10 |

上表的 `logical trials` 是每类 test 10 个 source × 2 条消息，因此每类为 20。source-level
两消息均成功的确切汇总见下表：

| 方法 | Speech | Music | Environment | 总计 |
|---|---:|---:|---:|---:|
| B1 8-bit wrapper | 7/10 | 6/10 | 7/10 | 20/30 |
| Candidate | 6/10 | 4/10 | 6/10 | 16/30 |

由于每类只有 10 个 test source，主结论以 source-disjoint 的 trial 表和总 source 计数为准：

- B1：`49/60` exact，BER `0.033333`，source-level 两条消息均成功 `20/30`。
- Candidate：`39/60` exact，BER `0.054167`，source-level 两条消息均成功 `16/30`。
- 因此候选在本 R1 test 上没有改善冻结 B1 的 MP3 消息恢复。

### 3.2 No attack

| 方法 | Speech exact | Music exact | Environment exact | 总 exact |
|---|---:|---:|---:|---:|
| B1 8-bit wrapper | 20/20 | 20/20 | 20/20 | 60/60 |
| Candidate | 13/20 | 13/20 | 17/20 | 43/60 |

候选在 no-attack 真实音频上已经出现 bit error，说明其失败不只是 MP3 codec drift。

## 4. matched-fidelity 检查

本轮使用相同 source、消息和 MP3 条件进行配对，但两方法的嵌入失真并未自然匹配，
因此 `MATCHED_FIDELITY = FAIL_AS_COMPARISON_GATE`，不能把候选与 B1 的差异解释为
公平的等音质比较。

独立 test 的 MP3 配对平均值：

| 方法 | 嵌入 SNR | log-spectral distortion RMS | MP3 fidelity SNR |
|---|---:|---:|---:|
| B1 8-bit wrapper | 57.144 dB | 0.0241 dB | 25.949 dB |
| Candidate | 46.299 dB | 0.0731 dB | 25.935 dB |

候选使用了明显更大的嵌入失真，仍未达到 B1 的 MP3 exact recovery；这支持“当前候选
不应升级为 V3-P1”，但不能声称已经完成严格的 matched-fidelity 优胜证明。

未执行正式主观听感实验，`FORMAL_PERCEPTUAL_GATE = NOT_ESTABLISHED`。

## 5. B1 真实音频逐物理位审计

完整逐位结果位于
`experiments/v3_p0_r1/V3_P0_R1_QIM_PER_BIT_STATS.csv`，每行包含 host、marked、MP3
统计量、重复观测、判决边界距离、host 载波能量和符号翻转标记。

test split 的均值：

| 类别 | host→marked sign flip | marked→MP3 sign flip | marked boundary distance | MP3 boundary distance | low-energy carrier fraction |
|---|---:|---:|---:|---:|---:|
| Speech | 0.5156 | 0.0875 | 1.2800 | 0.5422 | 0.8219 |
| Music | 0.5313 | 0.0813 | 1.2800 | 0.5748 | 0.8313 |
| Environment | 0.4969 | 0.1297 | 1.2800 | 0.4971 | 0.7969 |

解释：

1. B1 host→marked 变化约为一半，符合 QIM 将 host difference 推向 bit lattice 的行为，
   不是“嵌入没有改变 host”的现象。
2. MP3 后仍有类别相关的边界距离和符号翻转差异；Environment 的 marked→MP3 翻转最高，
   其 8-bit wrapper BER 也最高。
3. 所有类别的大比例 low-energy carrier 标记说明载波能量与内容有关，但本报告不据此
   固化新的 content-aware selector。
4. 因而 P0 的“content-dependent log-magnitude drift”在真实音频上仍得到支持，但应
   限定为本 manifest、6 秒前缀、FFmpeg 128 kbps 和当前 selector 条件下的观察。

## 6. 可复现产物

- `configs/v3_p0_r1_real_audio_manifest.json`
- `experiments/v3_p0_r1/V3_P0_R1_PAIRED_RESULTS.csv`
- `experiments/v3_p0_r1/V3_P0_R1_QIM_PER_BIT_STATS.csv`
- `experiments/v3_p0_r1/V3_P0_R1_NEGATIVE_SCORES.csv`
- `experiments/v3_p0_r1/V3_P0_R1_RESULTS.json`
- `scripts/v3_p0_r1_freeze_manifest.py`
- `scripts/v3_p0_r1_experiment.py`

结果只包含统计量和来源 metadata，不包含 MUSAN 原始音频。
