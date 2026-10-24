# V3-P1 有限 A/B 试听协议

本文件是有限人工试听的预注册操作协议，不是正式感知质量实验。

## 选择

- 从 P1 test 中各选 Speech、Music、Environment 代表 source 各 1 条。
- 本轮预选入口为：`speech/librivox/speech-librivox-0094.wav`、
  `music/fma/music-fma-0103.wav`、`noise/free-sound/noise-free-sound-0141.wav`；这些路径
  只由本地 manifest 引用，原始文件不复制进仓库。
- 对每条 source 生成 clean、Soft-Code marked、Repeat-4 marked，以及对应 MP3 版本。
- 播放顺序使用随机化的 A/B 标签，不向试听者显示方法、消息或检测结果。
- 使用同一耳机/扬声器、同一音量；每段先播放 A，再播放 B，可重复一次。

## 记录

试听者只记录：`A/B 无明显差异`、`A 更好`、`B 更好`、`出现明显伪影`，以及可选的文字备注。
不记录算法成功率，不把单人非盲试听写成正式 MOS 或不可察觉性证明。

## 本轮状态

当前自动化运行环境没有完成实际人工播放和听感问卷，因此：

`PERCEPTUAL_GATE = NOT_ESTABLISHED`

报告中的 SNR、频谱失真和 clipping 统计是客观指标，不替代试听结论。
