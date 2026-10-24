# V3-P0-R1 盲检测与拒绝报告

## 1. 检测接口

本轮为 P0 keyed local-normalized soft-correlation 原型新增了轻量 presence score 和
拒绝判决，未改变 B1/QIM、payload、selector 或 Course V2 detector。

每个 bit 的重复统计量为 `r_1 ... r_n`。presence score 定义为：

```text
bit_score = |mean(r)| * |mean(r)| / mean(|r|)
presence_score = mean(bit_score over bits)
```

当某 bit 的重复观测符号冲突时，`|mean(r)| / mean(|r|)` 会下降；因此先取每个重复
绝对值再平均的虚假高 confidence 不会直接变成 presence certainty。该 score 是
diagnostic，不是 calibrated probability。

检测调用只接收 received audio、候选配置和 key/seed。CSV 中
`detector_expected_payload_used = False`；真实消息只在实验结束后用于计算 BER/exact
recovery，不进入检测过程。

## 2. Calibration 与冻结

候选参数固定为 P0 开发点 `strength=0.02`、8 bits、16 repetitions/bit、seed 23。
presence threshold 只使用 dev split：

| 项目 | 结果 |
|---|---:|
| threshold | `0.07846780628511643` |
| dev positive conditions | 120 |
| dev positive detection | 116/120 = 96.67% |
| dev negative conditions | 120 |
| dev false-positive rate | 8/120 = 6.67% |
| test 是否重新调阈值 | 否 |

negative conditions 包含 30 个 dev source 的 clean、clean MP3 和正确嵌入音频的 wrong-key
MP3 试验。它们是拒绝诊断条件，不应被误解为 120 个独立 source recordings。

## 3. 独立 test 判决

### 3.1 正样本

| 类别 | No attack accepted | MP3 accepted | No attack exact | MP3 exact |
|---|---:|---:|---:|---:|
| Speech | 20/20 | 19/20 | 13/20 | 13/20 |
| Music | 19/20 | 16/20 | 13/20 | 11/20 |
| Environment | 19/20 | 19/20 | 17/20 | 15/20 |
| 总计 | 58/60 | 54/60 | 43/60 | 39/60 |

“accepted” 只表示 presence gate 接受；accepted 但 payload 错误属于 wrong-message
acceptance，而不是成功识别。MP3 正样本中有 `54 - 39 = 15` 个 accepted-but-wrong
message trials；no-attack 中有 `58 - 43 = 15` 个。

### 3.2 无水印与错误 key

| test negative 条件 | 条件 trials | accepted | source-level accepted |
|---|---:|---:|---:|
| clean | 30 | 3 | 3/30 = 10.0% |
| clean MP3 128k | 30 | 3 | 3/30 = 10.0% |
| wrong key on marked MP3 | 60 | 4 | 2/30 source = 6.67% |

这里的 clean 与 clean MP3 FPR 以 source recording 为单位报告；每个 source 在两个消息
trial 下只有一个无水印音频，两个 condition 分别统计。wrong-key 使用 30 个 test source
和两个已嵌入消息，因此显示 60 个条件 trial，同时补充 source-level 计数。

具体误接受样本：

| record | category | condition | score |
|---|---|---|---:|
| `r1-speech-test-0134-speech-librivox-0056` | Speech | clean | 0.094455 |
| 同上 | Speech | clean MP3 | 0.099632 |
| `r1-environment-test-0134-noise-free-sound-0079` | Environment | clean | 0.089201 |
| 同上 | Environment | clean MP3 | 0.082989 |
| `r1-music-test-0134-music-fma-0074` | Music | clean | 0.079542 |
| 同上 | Music | clean MP3 | 0.080915 |
| `r1-speech-test-0134-speech-librivox-0057` | Speech | wrong key | 0.105619 / 0.101630 |
| `r1-music-test-0134-music-fma-0017` | Music | wrong key | 0.094917 / 0.094226 |

这说明当前 score/threshold 不能提供可靠的无水印拒绝，也不能把“最近的消息”无条件
当作可信身份；系统应保留 UNKNOWN，而本轮候选没有达到可上线拒绝能力。

## 4. 统计限制

test 只有 30 个独立 source recordings，clean FPR 的 3/30 不能支持“低于 1%”或其他
低误报率正式结论。多个消息 trial 是 paired observations，不是新的独立音频来源。
阈值未因上述 test 误接受而回调。

完整原始判决数据：

- `experiments/v3_p0_r1/V3_P0_R1_NEGATIVE_SCORES.csv`
- `experiments/v3_p0_r1/V3_P0_R1_PAIRED_RESULTS.csv`
