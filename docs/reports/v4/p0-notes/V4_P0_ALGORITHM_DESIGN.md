# V4-P0 算法设计与实验边界

状态：`DESIGN_FROZEN_FOR_P0`（不是 V4-P1 算法承诺）

## 目标

在不改动 V3-RC1 代码和历史结果的前提下，验证一个真正改变嵌入通道的
时频候选是否值得继续研究。P0 只使用 6 秒、48 kHz 单声道音频和少量
开发来源；结果不能被称为独立泛化验证。

## 候选：V4-TF-SS

`audio_watermark.v4_tf` 使用：

1. 对带反射边界 padding 的音频做 Hann-window STFT，并以 overlap-add
   合成；嵌入为对数幅度扰动，保留每个频点原始相位。
2. 用公开 seed 为每个时频帧确定性选择频带内载波 bin 和平衡正负号；
   bit 按帧循环分配到整个 6 秒，而不是只占固定 32 个物理位置。
3. 每帧用载波局部能量估计得到可解释的 salience 权重。低能量 bin 权重
   较低，高能量 bin 才承担更多扰动；总 log-amplitude 扰动被 strength
   上限约束。
4. 检测器只重新计算接收音频的 STFT、公开载波和局部权重，先对每帧的
   signed correlation 做等权聚合，再输出 bit、score、presence score、
   margin 和 UNKNOWN 判决。它不读取 clean audio、消息或嵌入端搜索记录。

P0 的初始开发配置固定为 `n_fft=2048`、`hop_length=512`、载波频带
1.5--12 kHz、每帧 96 个 bin、seed 20261025；strength 只在预注册的
`0.04` 和 `0.08` 两个开发候选中观察，不进行无限搜索。8-bit 和 16-bit
使用相同物理规则，只有 payload 位数不同。

## 统一评价

新增 `audio_watermark.evaluation` 只定义与算法无关的结果结构和适配器
协议。V3、V4 和外部模型通过 adapter 进入同一个 scorer；第三方模型核心
不被修改。每个结果同时保存 native payload bits、effective payload bits、
sample rate、minimum length、condition、SNR/LSD/clipping、运行时间和
reject reason。

## 预算与停止条件

- 外部模型：优先 WavMark 一次真实嵌入、一次真实 FFmpeg MP3 128 kbps
  回环；AWARE/SilentCipher 仅在现有环境和已获取权重可直接运行时继续。
- V4-TF：每类最多 3 个开发来源、每个强度、8/16 bit、clean/MP3，消息
  使用预先固定的两个 seed；不使用 V3 正式测试集作新颖独立证据。
- 若候选在相近 SNR 下没有稳定改善，或没有可校准的 blind rejector，
  P0 结论为 `NO_GO`，不追加更复杂 ECC、训练或参数扫描。

## 许可与可复现性

第三方代码/权重只作为外部依赖或黑盒 adapter 记录。GPL 项目不得复制到
MIT 仓库。模型仓库 SHA、权重 SHA256、运行时、FFmpeg 命令、来源 manifest
和 seed 写入 P0 报告及实验 JSON；音频原始文件不写入 Git。
