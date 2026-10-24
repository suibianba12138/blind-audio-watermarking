# V3 P0 Recommendation

## Final gate

```makefile
V3_P0_STATUS = PARTIAL
QIM_FAILURE_MECHANISM = CONFIRMED_CONTENT_DEPENDENT_MP3_LOG_MAGNITUDE_DRIFT_WITH_CORRELATED_REPETITIONS
AUDIOWMARK_REVIEW = REVIEWED_NOT_REPRODUCED_GPL_ISOLATED_CLI_REQUIRED
WAVMARK_REPRODUCTION = BLOCKED_ENVIRONMENT_NO_TORCH_OR_TORCHAUDIO
SILENTCIPHER_FEASIBILITY = REVIEWED_NOT_RUN_PYTORCH_AND_CHECKPOINT_REQUIRED
SPREAD_SPECTRUM_PROTOTYPE = PASS_SYNTHETIC_DEVELOPMENT_ONLY
MATCHED_FIDELITY_COMPARISON = PARTIAL_SYNTHETIC_ONLY_NO_LEGAL_INDEPENDENT_TEST
RECOMMENDED_V3_ARCHITECTURE = HOLD_KEYED_LOCAL_NORMALIZED_SOFT_CORRELATION_AS_CANDIDATE_ONLY
GO_NO_GO = NO_GO_FOR_V3_P1
```

## Decision

本阶段 **不进入 V3-P1**。原因不是原型在合成 probe 上没有信号，而是进入 P1 的必要
证据尚未建立：

1. 没有经过来源和许可核验的音乐、语音、环境音 dev/test split；
2. 没有在独立 test 上比较冻结 B1 与候选方法；
3. 候选原型没有 rejector，FPR / FAR / error acceptance 未建立；
4. WavMark、SilentCipher、AudioSeal 等强基线没有在隔离依赖环境中本地推理；
5. 没有正式主观音质实验；
6. 合成 probe 上的 1-bit/8-bit 结果不能外推为 32-bit 任意消息恢复。

## 机制结论

冻结 QIM 的主要问题是 codec 后 selected A/B log-magnitude difference 漂移，而不是
无攻击嵌入无法形成可检测格点。该漂移对内容类别非常敏感：当前 synthetic
speech/environment probe 在 FFmpeg MP3 后分别出现 0.375 和 0.40625 BER，而
music-like probe 为 0；四次 repetition 的 MP3 statistic correlation 也从约 0.96
到接近 0 变化。这个证据支持后续关注载波能量、局部归一化、软统计和跨 frame 证据，
但不支持当前冻结算法或任何候选方法已经具有泛化 robustness。

## 对候选方向的建议

保留 `keyed_spread_spectrum_local_norm` 作为下一轮候选，而不是公开算法：

- 它在 1-bit/8-bit synthetic development probe 上可重复，且真实 FFmpeg MP3 往返
  可运行；
- 其强度与 SNR 有单调 trade-off，`strength=0.02` 是本轮相对接近 fidelity budget
  的开发点，但不是冻结参数；
- 仍需要加入盲拒绝机制、错误接受率测试、真实 source-disjoint 数据和正式音质门；
- 不应在获得这些证据前加入 ECC、codec-aware selector、content-aware policy 或
  修改 Course V2。

## 下一步（若重新授权进入 P0.5/P1）

1. 先建立并审计小型、明确许可的 music/speech/environment source manifest；
2. 在独立第三方环境补齐 WavMark CPU inference，保存版本、权重 hash、运行时间和
   内存峰值；
3. 用同一 source-disjoint protocol 对 B1、WavMark 和候选原型做 1/8-bit 与 32-bit
   分层评估；
4. 在 dev 上设计 rejector，再在未使用 test 上一次性计算 FPR/FAR；
5. 只有 matched fidelity 下 BER 和完整消息恢复均有独立改善，且音质/误报没有明显
   退化，才把候选升级为 V3-P1。

论文、README 或课程网页中的历史指标没有被本报告重新解释为本地复现结果。
