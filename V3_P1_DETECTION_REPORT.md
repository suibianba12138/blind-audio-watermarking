# V3-P1 盲检测与拒绝报告

结果文件：

- `experiments/v3_p1/V3_P1_DETECTION_RESULTS.csv`
- `experiments/v3_p1/V3_P1_ANALYSIS.json`

所有 threshold 固定来自 Pilot/config freeze；P1 negative 没有参与重新校准。统计中同时
给出 trial-level 与 source-level，Wilson 区间使用 95% score interval。

## P1 test negative controls

| 方法 | clean FPR | clean-MP3 FPR | 合并 clean/MP3 trial FPR | wrong-key MP3 acceptance | positive wrong-message acceptance |
|---|---:|---:|---:|---:|---:|
| Repeat-4 | 0/30 | 1/30 | 1/60 (1.67%) | 2/60 (3.33%) | 14/60 (23.33%) |
| Hard-Code | 0/30 | 1/30 | 1/60 (1.67%) | 2/60 (3.33%) | 2/60 (3.33%) |
| Soft-Code | 0/30 | 0/30 | **0/60 (0%)** | **0/60 (0%)** | **0/60 (0%)** |

Soft-Code 合并 clean/MP3 FPR 的 Wilson 95% CI 为 `[0%, 6.02%]`；wrong-key acceptance
同样为 `[0%, 6.02%]`。source-level clean/MP3 任一接受的上界为 `11.35%`（0/30）。
因此这些结果不能写成总体 FPR `<1%` 的证明。

Repeat-4/Hard-Code 的 1 次 clean-MP3 误报来自同一个 source-level negative；Repeat-4
wrong-key 的 2/60 是 2 个 trial、2 个 source-level accepts，Hard-Code 同样为 2/60。

## Blind contract

检测调用只接收 received audio、冻结 config、公开 selector/错误 selector。expected payload、
clean audio、身份、文件名答案和缓存答案都不进入 detector。expected payload 只在返回结果后
用于计算 BER/exact/wrong-message 指标。

## Pilot wrong-key 2/60 复核

Pilot `soft_code@1.60` 的两次错误密钥接受：

| source | category | message trial | presence score | frozen threshold |
|---|---|---|---:|---:|
| `r1-music-test-0194-music-fma-0030` | Music | seed_101 | 0.87537 | 0.78551 |
| `r1-music-test-0194-music-fma-0030` | Music | seed_202 | 0.84583 | 0.78551 |

两条记录属于同一 source，说明该 Pilot 现象不能按 2 个独立音频计算；最保守解释是
该 source 的 received spectrum 在错误 selector 下也产生了较高 code correlation。
这是内容相关诊断，不是已证明的单一因果机制。P1 未按此样本做补丁，也没有改变 threshold。

## 结果边界

Soft-Code 的 P1 negative 结果优于两个对照，但总负例仍只有 60 clean/clean-MP3 trial 和
60 wrong-key trial。不能从有限零误报样本推出部署级低误报率，也不能把 presence score
当作 calibrated probability。
