# V3-P0-R1 决策

## 最终字段

```makefile
R1_STATUS = PARTIAL
REAL_AUDIO_DATA = PASS_METADATA_ONLY_60_SOURCE_RECORDINGS
QIM_DRIFT_REAL_AUDIO = CONFIRMED_WITH_SCOPE_LIMITS
V3_REAL_AUDIO_MP3_BER = B1_8BIT_WRAPPER_0.033333_TEST_VS_CANDIDATE_0.054167_TEST
V3_EXACT_MESSAGE_RECOVERY = B1_49_OF_60_TEST_VS_CANDIDATE_39_OF_60_TEST
MATCHED_FIDELITY = FAIL_AS_COMPARISON_GATE
NEGATIVE_REJECTION = FAIL_TEST_CLEAN_FPR_3_OF_30_AND_WRONG_KEY_ACCEPTANCE_4_OF_60
WAVMARK_CPU_BASELINE = BLOCKED_NO_LOCAL_TORCH_TORCHAUDIO_OR_WEIGHT
V3_P1_READINESS = NO_GO
```

## 决策依据

1. 真实音频恢复已完成：三类各 10 dev + 10 test，split 按源文件或更高层级来源组，
   manifest 冻结且不向仓库复制原始音频。
2. 冻结 B1 的真实 MP3 逐物理位统计已经保存。P0 观察到的 content-dependent
   log-magnitude drift 在本 manifest 和 FFmpeg 128 kbps 条件下仍可见，但不能外推到
   所有音频或所有 codec。
3. 候选在 test MP3 上 BER `0.054167`、exact `39/60`，低于 B1 8-bit wrapper 的
   BER `0.033333`、exact `49/60`。候选 no-attack 也不是零 BER（`43/60` exact）。
4. 候选嵌入 SNR 约 `46.299 dB`，B1 约 `57.144 dB`；失真预算没有匹配，因此
   `MATCHED_FIDELITY` 不通过，不能宣称公平优胜。
5. dev-only calibration 没有采用 reject-all，但 test clean FPR 为 `3/30` source，
   clean MP3 也是 `3/30`，wrong-key marked MP3 有 `4/60` accepted trial。拒绝机制
   仍不足以支持可靠课程或公开系统身份判决。
6. WavMark 未能在本机复现：当前隔离 Python 为 3.13.5，无 `torch`、`torchaudio`、
   `wavmark` 或本地预训练权重；磁盘约 95 GB 可用，但依赖/权重获取和兼容性未建立。
   因此不能把 WavMark 论文或官方 README 指标写成本地结果。WavMark 的公开接口和许可
   资料仅作为待复现基线记录：[official repository](https://github.com/wavmark/wavmark)。

## 停止边界

本轮不进入 V3-P1，不继续扩大参数搜索，不添加 ECC/FEC、content-aware strength、
新的 codec selector 或新的数据集。保留候选代码和全部失败证据，下一次若重新授权，
应先独立解决 rejector 与 matched-fidelity protocol，再决定是否值得继续算法扩展。

本报告不声称 robustness、感知不可察觉性或任意 32-bit 消息恢复已经验证；正式主观
音质门仍为 `NOT_ESTABLISHED`。

## 外部资料与本地证据边界

- MUSAN/OpenSLR 页面：数据来源和父级许可引用；不是本地重新下载或再分发声明。
- WavMark 官方仓库：接口、依赖和待复现基线说明；不是本地推理结果。
- `experiments/v3_p0_r1/`：本地 60-source、6 秒、真实 FFmpeg 128 kbps 结果。
