# V3-P1 独立泛化验证

状态：`V3_P1_STATUS = PASS_WITH_LIMITATIONS`

本报告只使用 P1 新冻结 manifest 的证据。Pilot 结果单独作为历史参照，不与 P1 合并。
冻结的 B1/Course V2 实现、公开网站、SPL 论文数据和 Render 均未修改。

## 1. 冻结协议

| 项目 | 固定内容 |
|---|---|
| 分支 | `research/v3-p1`，从 `34411a9` 创建 |
| manifest | `configs/v3_p1_independent_manifest.json`，SHA256 `6c5f4d63c9659f4332dd3242360806091d1672fdbe696f3bae06516b7f32a0e6` |
| 来源 | 本地 MUSAN metadata 指向的真实录音；原始音频不入 Git |
| 总 source | 60：Speech/Music/Environment 各 20 |
| split | 各类 10 dev + 10 test；按 source recording/FMA license group 分组 |
| 与 R1/Pilot 重合 | 路径与 SHA256 均为 0 |
| 消息 | 两个固定 8-bit 消息，seed `101/202`；同一 source 内是 paired trials |
| 音频 | 48 kHz、mono、6 秒前缀；同一 source 给三种方法 |
| strength | 固定 `1.60` |
| codec | FFmpeg 6.1.1、`libmp3lame`、128 kbps |
| threshold | Repeat-4/Hard-Code `0.47678591988959035`；Soft-Code `0.7855073980199624` |

threshold、strength、selector、代码 SHA256 记录在
`experiments/v3_p1/CONFIG_FREEZE.json`，没有用 P1 test 重新拟合。

## 2. 三组对照

- **Repeat-4 B1**：每个 8-bit logical bit 重复到 4 个物理位，使用冻结 B1 hard detector。
- **Hard-Code B1**：使用与 Soft-Code 相同的固定 `[32,8,8]` 码本，但只对 32 个 hard
  physical bits 做最小汉明距离解码。
- **Soft-Code B1**：使用同一码本和冻结的连续 QIM signed statistics，做 normalized
  soft correlation 解码。

三种方法使用同一 source、同一消息、同一 6 秒长度、同一 B1 embedder、同一 selector、
同一 MP3 encoder。`physical BER` 与 `logical BER` 分开记录；逻辑 BER 的下降不能解释为
物理 MP3 信道 BER 下降。

## 3. P1 test 结果

正式 test 是 30 个独立 source、每个 2 条消息，共 60 条 paired message trials。

### 3.1 MP3 128 kbps

| 方法 | Physical BER | Logical BER | decoded exact | accepted exact | source 两消息均 exact |
|---|---:|---:|---:|---:|---:|
| Repeat-4 | 0.06302 | 0.03333 | 46/60 (76.67%) | 46/60 | 20/30 (66.67%) |
| Hard-Code | 0.06458 | 0.00833 | 58/60 (96.67%) | 58/60 | 28/30 (93.33%) |
| Soft-Code | 0.06458 | 0.00000 | 60/60 (100%) | 59/60 | 30/30 (100%) |

Wilson 95% CI（trial-level exact）：Repeat-4 `[64.56%, 85.56%]`，Hard-Code
`[88.64%, 99.08%]`，Soft-Code `[93.98%, 100%]`。Soft-Code 有 1 条 decoded exact
消息的 presence score 低于冻结阈值，因此 detector 返回 reject；该条没有被改判为成功。
具体为 `r1-environment-test-0254-noise-free-sound-0141 / seed_202`，score
`0.732314`，threshold `0.785507`。

### 3.2 按内容类别

| 方法 | Speech exact | Music exact | Environment exact |
|---|---:|---:|---:|
| Repeat-4 | 13/20 (65%) | 15/20 (75%) | 18/20 (90%) |
| Hard-Code | 20/20 (100%) | 18/20 (90%) | 20/20 (100%) |
| Soft-Code | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |

Soft-Code 在三类内容上没有出现类别性下降；Repeat-4 的失败主要出现在 speech 和 music。
Hard-Code 的两个失败为 music source `...music-fma-0109 / seed_202` 与
`...music-fma-0113 / seed_101`。

### 3.3 No-attack

三种方法在 P1 test 的 clean marked 条件均为 `60/60` decoded exact，physical/logical
BER 均为 `0`。这只验证无攻击可读性，不替代 MP3 结果。

## 4. 匹配失真与性能

P1 test MP3 正样本的客观平均值：

| 方法 | Embedding SNR | LSD RMS | MP3 fidelity SNR | 平均 embed time | 平均 detect time |
|---|---:|---:|---:|---:|---:|
| Repeat-4 | 57.788 dB | 0.02939 dB | 25.975 dB | 0.0306 s | 0.0094 s |
| Hard-Code | 57.657 dB | 0.02992 dB | 25.976 dB | 0.0319 s | 0.0054 s |
| Soft-Code | 57.657 dB | 0.02992 dB | 25.976 dB | 0.0319 s | 0.0063 s |

Soft-Code 相对 Repeat-4 的平均 SNR 差为 `-0.131 dB`，LSD 差为 `+0.00053 dB`，因此
均值层面接近；source/message 配对的最大绝对 SNR 差为 `6.413 dB`，所以不能声称每个
source 都严格等失真。结论字段为：

`MATCHED_FIDELITY = PARTIAL_MEAN_SNR_MATCH`

进程级 `ru_maxrss` 最高约 `5032 MB`，该数值包含长源 WAV 解码/重采样期间的进程峰值，
不是单个 detector 的稳定常驻内存承诺。

## 5. Clipping 与试听

正式 test 中有 4 个 Environment source 本身已超过满幅，导致 8 条 message rows 的
`marked peak > 1.0`。这些 rows 的 `clean_clipping_flag=1`，嵌入后没有新增 clipping：
`introduced_clipping_flag = 0/60`。异常 source 为：

- `...noise-free-sound-0142`，clean peak `1.00916`；
- `...noise-free-sound-0143`，clean peak `1.00058`；
- `...noise-free-sound-0147`，clean peak `1.00058`；
- `...noise-free-sound-0153`，clean peak `1.00426`。

试听协议在 `experiments/v3_p1/PERCEPTUAL_REVIEW_PROTOCOL.md`。当前环境未完成实际人工播放，
因此：`PERCEPTUAL_GATE = NOT_ESTABLISHED`。

## 6. 配对统计

主要独立单位是 30 个 test source，每个 source 的两条消息先聚合为“两个消息均 exact”。

| 比较 | Soft/Hard 成功且 Repeat 失败 | Repeat 成功且 Soft/Hard 失败 | McNemar exact two-sided p |
|---|---:|---:|---:|
| Soft-Code vs Repeat-4 | 10 | 0 | 0.001953125 |
| Hard-Code vs Repeat-4 | 8 | 0 | 0.0078125 |

这支持在本 P1 source set 上的配对改善，但不把同一 source 的两条消息当成 2 个独立 source。

## 7. Pilot 与 P1 的边界

Pilot 是此前开发阶段的 60-source manifest；P1 使用另一个新 manifest，正式结论只使用
P1 test。Pilot 的 Soft-Code@1.60 wrong-key 2/60 来自同一条 Music source 的两条 paired
trials，两个 presence score 为 `0.87537` 和 `0.84583`，均超过 Pilot threshold；这说明
Pilot 中存在 source/content-specific high-correlation false acceptance。P1 没有把该 source
重新纳入，也没有用 P1 negative 重新拟合阈值。

P1 新 wrong-key test 为 Soft-Code `0/60`，但样本仍不足以宣称总体误报率低于 1%。
