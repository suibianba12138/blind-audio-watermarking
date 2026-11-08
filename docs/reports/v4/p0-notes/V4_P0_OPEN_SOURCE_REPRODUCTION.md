# V4-P0 开源强基线复现报告

状态：`LOCAL_REPRODUCTION_WITH_PARTIAL_EXTERNAL_COVERAGE`

本报告严格区分上游公开结果和本机运行结果。除 WavMark 的官方 wheel/权重外，
没有把第三方源码或模型复制进本仓库；外部文件位于 `[local path omitted] 和
`[local path omitted] Git 发布内容。

## 运行环境

| 项目 | 值 |
|---|---|
| 首选环境 | `[local path omitted] |
| Python | 3.8.20 |
| Torch / Torchaudio | 2.3.1 / 2.3.1 |
| 设备 | CPU；CUDA unavailable；无 NVIDIA GPU |
| FFmpeg | `/usr/bin/ffmpeg`, 6.1.1 |
| 机器人环境改动 | 否 |
| 新建 venv/conda | 否 |

## WavMark

上游版本：`wavmark/wavmark` main，审计时 SHA
`6ab3bf7ce0679e5b5cfeff3a62e8df9cd2024b37`。官方 wheel SHA256 为
`f77c7234e66b6983273fa7bd7509acaa9195cd936fd1c178b46c8e996d7e8f02`；官方
checkpoint `step59000_snr39.99_pesq4.35_BERP_none0.30_mean1.81_std1.81.model.pkl`
SHA256 为
`7a3d873d115c2c644685fb4cf109bdb299718296b88c871d3cf1c8e4cbc13144`。

实际运行命令：

```bash
PYTHONPATH=[local path omitted] \
  [local path omitted] \
  scripts/v4_p0_wavmark_probe.py \
  --source [local path omitted] \
  --checkpoint [local path omitted] \
  --output experiments/v4_p0/WAVMARK_REPRODUCTION.json
```

本地结果：

- 1 秒、16 kHz、单声道工作块，CPU 推理；
- 32 个模型位，其中前 16 位是固定 identification pattern，后 16 位是
  custom payload；这不是任意 32-bit 有效消息能力；
- clean 直接解码 BER=0；
- 真实 FFmpeg `libmp3lame -b:a 128k` 编解码后 BER=0、exact recovery；
- watermarked-vs-clean SNR = 33.957 dB；encode 约 0.449 s，decode 约
  0.319 s；MP3 文件约 17,901 bytes；
- 仅完成单块、单个本地 music source。官方多块 helper 在本轮限定运行窗口内
  没有产生可记录的 6 秒结果，因此不声称 WavMark 的长音频结果已经复现。

上游协议和模型说明来自 [WavMark 官方仓库](https://github.com/wavmark/wavmark)
及其 [官方 Hugging Face 模型页](https://huggingface.co/M4869/WavMark)。
上游论文或 README 指标没有填入本地结果表。

## AWARE

官方 `deepmark/aware` main SHA：
`402041acf65eeb3f03a09381ace9f091ac318cef`。仓库公开 MIT 许可，但本机没有
对应包、权重或已审查的独立运行环境。本轮未安装依赖、未下载权重、未运行推理，
因此：`AWARE_REPRODUCTION = BLOCKED_NO_LOCAL_RUNTIME_OR_WEIGHTS`。

## SilentCipher、AudioSeal、CRAW、OmniSealBench

| 项目 | 审计版本 | 本地状态 |
|---|---|---|
| SilentCipher | `sony/silentcipher` master `c11afe0e2df73f1ac0f848e2903b8af36e6a0b10` | 未运行；缺少其音频/模型依赖和权重 |
| AudioSeal | `facebookresearch/audioseal` main `e63a8a0e5cdf7bb797159c92ba15961557fe9bd2` | 未运行；缺少独立 Torch/权重准备 |
| CRAW | `DavidC1212/craw` main `bd8318cf0000d2db51637bbfedbe6778df598eb2` | 仅审查；未确认完整第三方许可链，不复制源码 |
| OmniSealBench | main `bd141394a0dfeac0b4cfedfdb4feaebb2a2c6db6` | 仅审查；benchmark/model licenses 需分开核对 |

这些项目的公开论文结果、README 数字和本地 WavMark 单块结果不构成相互可比的
6 秒 V4 排名。后续若继续，必须为每个模型保留原生采样率、最小长度、消息定义、
权重许可和检测规则。
