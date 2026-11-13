# 数字音频水印系统｜DSP 课程设计

本项目围绕数字音频的附加信息嵌入与恢复，完成了一套**参考辅助的多频带数字音频水印系统**。主要目标是在尽量保持音乐音质的前提下，让信息经过常见音频处理后仍有机会被恢复，并提供不同容量与可靠性侧重的工作模式。

**当前课程最终版：** [C2/C3 源码、示例与音频](course_release/) · [English README](README.md) · [历史版本归档](archive/README.md)

> **使用条件：** 检测时需要对应的**无水印原音**和密钥，但不向检测器提供预期消息。本方案是**参考辅助（非盲）水印**，适合受控音频分发和课程信号处理演示，不是可直接用于版权取证的安全认证系统。

## 项目实现了什么

```text
原始音频 + 数字消息 + 密钥
          ↓
分帧 FFT → 密钥控制的 chip 分配 → 多频带相对能量调制
          ↓
      带水印音频
          ↓
   MP3 / AAC / 音量变化 / 重采样
          ↓
接收音频 + 原音参考 + 密钥
          ↓
对齐 → 频带差分 → chip 聚合 → 消息判决与存在性检查
          ↓
     恢复消息 / UNKNOWN
```

两种工作模式使用相关的频域嵌入与参考辅助检测方法，但信息组织不同：

| 工作模式 | 每 6 秒载荷 | 72 秒信息组织 | 独立信息量 |
| --- | --- | --- | --- |
| **高可靠身份模式 C2** | 8 bit | 32-bit ID 拆成四个字节，每 24 秒重复一次，共三轮 | **32 bit** |
| **高容量模式 C3-16** | 16 bit | 12 个不同的 16-bit 消息块 | **192 bit** |

**重要区别：** C2 的 72 秒共发送 96 bit 编码数据，但重复身份模式的**独立信息只有 32 bit**。C3-16 的 192 bit 则是 12 块不同消息组成的独立信息。不要将两种口径混用。

## 真实音乐演示

精选曲目为 **Where You Are Now**（Benjamin Orth，featuring Wolf Fly），使用连续 **72 秒**片段。音频采用 [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)，署名和改动说明见 [第三方素材与许可](course_release/THIRD_PARTY_NOTICES.md)。

已发布的 [演示素材](course_release/media/selected_c3_16_showcase/) 包括原音 WAV、水印 WAV、整段 MP3/AAC、实际检测记录、波形和频谱图。

在这首精选音乐上，C3-16 的结果为：

- **192 bit**：12 个独立 16-bit 消息块，覆盖 72 秒。
- **Clean WAV / MP3 128 kbps / AAC-LC 128 kbps**：每种条件均 **12/12 块正确**，完整消息一致。
- **扩展处理**：MP3→AAC、音量 −6 dB、音量 +3 dB、48→44.1→48 kHz 重采样后，完整消息也成功恢复。
- **音质**：该案例嵌入 SNR 约 **45 dB**；未开展正式主观听音实验。

这是为了课堂展示选取的**一个真实成功案例**，不是对任意音乐的总体性能保证。

## 实验性能与边界

| 测试协议 | Clean | MP3 128 kbps | AAC-LC 128 kbps |
| --- | ---: | ---: | ---: |
| C2：60 条独立 6 秒音频（Locked Test） | 60/60 | 59/60 | 57/60 |
| C3-16：120 条独立 6 秒音频 | 120/120 | 120/120 | 103/120 |
| C3-16：精选 72 秒音乐（每块） | 12/12 | 12/12 | 12/12 |

表格统计的是各协议下**正确接受**的消息/块。C3-16 在独立 AAC 测试中另有 **11/120 错误消息被接受**和 6/120 UNKNOWN；在 10 条 Development 随机混合的 72 秒音频上，AAC 完整消息恢复为 **2/10**，MP3→AAC 为 **6/10**。因此不能把精选案例的成功结果描述为普遍的 AAC 鲁棒性。

32-bit C2 重复身份模式在另外 **20 条 72 秒随机混合音频**上，Clean、MP3、AAC 三种条件的完整身份融合恢复均为 **20/20**；它使用的是不同的消息容量和评估协议，不能与 192-bit 完整消息成功率直接比较。

详细的负例、错误接受和评估条件见 [EVIDENCE_SUMMARY.md](course_release/EVIDENCE_SUMMARY.md)。

## 运行课程最终版

依赖：**Python 3.10+、NumPy、SciPy**；执行 MP3/AAC 转码还需安装 **FFmpeg**。

```bash
git clone https://github.com/suibianba12138/blind-audio-watermarking.git
cd blind-audio-watermarking/course_release
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
```

以公开演示密钥在真实音乐的前 6 秒嵌入并回读检测 16-bit 消息：

```bash
python examples/embed_detect_6s.py \
  --mode c3-16 \
  --reference media/selected_c3_16_showcase/Original.wav \
  --message A7C3 \
  --key course-demo-public-v1 \
  --output /tmp/course-watermarked.wav
```

72 秒 32-bit 重复身份、192-bit 消息，以及实际 FFmpeg 编解码示例，请看 [课程发布包中文说明](course_release/README_ZH.md)。

**注意：公开 Demo Key 与冻结实验的密钥不同。** 不能用公开密钥重新检测历史精选水印文件，再把结果称为对冻结实验的复现。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| [`course_release/`](course_release/) | **当前主版本**：C2/C3 源码、示例、测试、音频和实验依据 |
| [`archive/`](archive/) | V2/V3/V4 历史说明与旧 README 快照 |
| [`src/`](src/)、[`app/`](app/) | **历史 V3** 代码，保留以维持在线演示兼容性 |
| [`docs/`](docs/) | 原有 V2/V3 文档及尚未更新的 V4 静态网站 |
| [V4 历史快照分支](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113) | 独立的神经盲水印 Studio |

## 历史版本归档

项目曾尝试过不同算法，**但它们的检测条件与实验协议并不相同**：

- [**V2**：四身份分类水印](archive/v2/README.md)。历史 32-bit 冗余码字实际只表示 **2 bit 身份信息**。
- [**V3**：FFT/QIM + Soft-Code 盲水印](archive/v3/README.md)。8-bit 消息，代码保留；[独立快照分支](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v3-legacy-20261113)。
- [**V4**：神经盲水印 Studio](archive/v4/README.md)。40-bit，基于 Sony 第三方预训练 SilentCipher；[独立快照分支](https://github.com/suibianba12138/blind-audio-watermarking/tree/archive/v4-studio-20261113)，[历史 Draft PR #5](https://github.com/suibianba12138/blind-audio-watermarking/pull/5)。

**网站状态：** [个人网站上的音频水印项目页](https://shengkaini.com/blind-audio-watermarking/) **仍展示历史 V4 内容**；[Render 在线演示](https://blind-audio-watermarking-demo.onrender.com/) 仍是 **V3**。它们尚不是 C2/C3 的在线处理系统。后续网站更新与部署将单独进行。

## 许可与适用范围

课程实现代码采用 [MIT 许可](LICENSE)，演示音乐遵循 **CC BY 3.0**（不是 MIT），详见 [第三方声明](course_release/THIRD_PARTY_NOTICES.md) 和 [源码出处说明](course_release/SOURCE_PROVENANCE.json)。

本系统要求匹配的原音参考，更适合已知音源且基本完整的音频。尚未验证任意截取、恶意去水印、大规模原曲检索或版权真实性的密码学证明。

*2026 DSP 课程设计 · 多频带调制 · 参考辅助检测*
