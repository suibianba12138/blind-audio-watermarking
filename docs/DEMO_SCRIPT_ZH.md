# 中文现场演示脚本

## 事前准备

1. 执行 `python -m app.gui`，确认页面地址为本机 `127.0.0.1`。
2. 准备一段经允许使用的 WAV；也可用
   `python examples/generate_test_audio.py` 生成测试音频。
3. 确认 FFmpeg 可执行：`ffmpeg -version`。

## 现场流程

1. 上传 WAV，选择一个身份和 `6 seconds`。
2. 点击 `Embed watermark`，试听原音频和水印音频。
3. 点击 `Encode real MP3 128 kbps`，试听压缩后解码音频。
4. 点击 `Blind detect`，观察 `DETECTED: UESTC-XXX` 或
   `UNKNOWN / NO VALID WATERMARK`、距离、阈值、时间块数量和置信度诊断值。
5. 切换另一个身份或音频重复一次。
6. 选择 `NO WATERMARK` 生成负对照，压缩后检测应允许返回 UNKNOWN；不把
   负对照强行解释为某个合法身份。

## 讲解边界

- 检测器不会读取选择的 expected identity；该选择只用于嵌入阶段。
- “confidence” 是诊断量，不是校准概率。
- 课程冻结结果中正式可靠性证据是 6 秒/1 块；15/30 秒是实际重复块的
  演示路径，不应现场声称已有同等规模正式验证。
- 正式感知实验没有建立，不能宣称不可察觉。
