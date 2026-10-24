# V3-P1 决策

## 最终字段

```makefile
V3_P1_STATUS = PASS_WITH_LIMITATIONS
INDEPENDENT_SOURCE_COUNT = 60_TOTAL; 30_FORMAL_TEST_SOURCES
REPEAT4_EXACT_RECOVERY = 46_OF_60_TRIALS; 20_OF_30_SOURCES_BOTH_MESSAGES
HARDCODE_EXACT_RECOVERY = 58_OF_60_TRIALS; 28_OF_30_SOURCES_BOTH_MESSAGES
SOFTCODE_EXACT_RECOVERY = 60_OF_60_DECODED; 59_OF_60_ACCEPTED; 30_OF_30_SOURCES_BOTH_MESSAGES
PAIRED_IMPROVEMENT = SOFT_VS_REPEAT_PLUS_10_OF_30_SOURCES; MCNEMAR_P_0.001953125
MATCHED_FIDELITY = PARTIAL_MEAN_SNR_MATCH
NEGATIVE_FPR = SOFT_CLEAN_AND_CLEAN_MP3_0_OF_60_TRIALS; WILSON_UPPER_6.02_PERCENT
WRONG_KEY_ACCEPTANCE = SOFT_0_OF_60; WILSON_UPPER_6.02_PERCENT
PERCEPTUAL_GATE = NOT_ESTABLISHED
V3_P2_READINESS = CONDITIONAL_GO
```

## 决策依据

1. P1 使用了新的 60-source manifest，正式 test 为 30 个未参与 Pilot 的 source，且
   Speech/Music/Environment 各 10 个 test source。
2. Soft-Code 在相同 B1 embedder、strength、音频长度和 FFmpeg 128 kbps 下，physical
   BER 为 `0.06458`，与 Repeat-4 的 `0.06302` 同量级；logical BER 从 `0.03333`
   降至 `0`，说明改善来自码字 soft decoding，而不是伪称物理信道改善。
3. Soft-Code decoded exact 为 `60/60`，冻结 reject threshold 下 accepted exact 为
   `59/60`；source-level 两条消息均成功 `30/30`。Hard-Code 也改善至 `58/60`，支持
   连续软信息相对 hard decision 的额外收益。
4. 三类内容均为 Soft-Code `20/20` exact；没有只依赖单一类别的证据。
5. Soft-Code clean/clean-MP3 FPR 和 wrong-key acceptance 均为 `0`，positive
   wrong-message acceptance 为 `0/60`。但负例数量不足以证明总体误报率低于 1%。
6. 平均 SNR 与 LSD 接近，但个别 source/message 的 SNR 差异最高约 `6.413 dB`，所以
   matched-fidelity 只能标记为 partial；没有正式人工感知实验。

## P2 边界

建议 `CONDITIONAL_GO` 只用于下一阶段预注册设计评审，不代表立即实现。进入 V3-P2 前应：

- 预先定义更严格的 source-level fidelity 匹配协议；
- 扩大独立负例并报告更窄的误报置信区间；
- 完成盲化人工试听或正式感知实验；
- 保持当前 P1 threshold/strength 不因 P1 test 结果回调。

V3-P2 的 16-bit、64 kbps MP3、AAC/Opus、WavMark 统一对照均未在本阶段实现。
