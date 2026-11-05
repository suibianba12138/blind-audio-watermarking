# V4-P2 SilentCipher 本地 MVP 报告

**日期：2026-11-05**\
**状态：`V4_P2_STATUS = PARTIAL`**\
**范围：本地单 worker Gradio MVP、官方权重 CPU 推理、P1 `music_03` 失败诊断；不是正式性能评估。**

## 结论

SilentCipher 已封装成可在本地运行的 44.1 kHz、40-bit 水印工具。实际运行的 Gradio 页面完成了音频上传、嵌入、WAV 下载、FFmpeg MP3 128 kbps 编解码、独立文件上传盲检、无水印拒绝和非法输入提示。模型加载一次，CPU 单 worker 排队，不执行 phase-shift 搜索。

本轮选择的真实音乐片段 clean 检测恢复正确消息并判为 `IDENTIFIED`；同一片段经真实 MP3 往返后仅生成低分错误候选并被判 `UNKNOWN`。这与 P1 的音乐 MP3 风险相符。因 MP3 正例没有恢复消息，MVP 的界面和链路已可用，但不能视为达到音乐 MP3 鲁棒性目标，故判 `PARTIAL`。

```text
V4_P2_STATUS = PARTIAL
GUI_RUNTIME = PASS (local Gradio API-driven end-to-end)
CLEAN_BLIND_DETECTION = PASS (one real music segment)
MP3_128K_ROUNDTRIP = PASS
MP3_POSITIVE_RECOVERY = FAIL (this music segment)
UNWATERMARKED_REJECTION = PASS (one negative)
PRESENCE_CALIBRATION = PROVISIONAL
```

## 1. `music_03` MP3 失败原因

用 P1 冻结的 `music_03` 片段、两条固定 40-bit 消息、官方 44.1 kHz 权重重放 clean 和真实 FFmpeg MP3 128 kbps。没有修改官方源码、权重或模型参数。脚本同时运行官方 `decode_wav()` 和独立追踪器；诊断数据保存在 [MUSIC03_DIAGNOSTIC.json](../../../experiments/v4_p2/MUSIC03_DIAGNOSTIC.json)，复现脚本为 [v4_p2_diagnose_music03.py](../../../experiments/v4_p2/prototype/v4_p2_diagnose_music03.py)。

| 消息 | 条件 | 官方状态 | 一致度 | 终止符 | 阶段结果 |
|---|---|---:|---:|---|---|
| A | clean | `True` | 0.869048 | 众数序列索引 20 | 完整消息 `[18,52,86,120,154]` |
| A | MP3 128k | `False` | 0.714286 | 未检测到 | `MISSING_TERMINATOR`，消息字节转换未执行 |
| B | clean | `True` | 0.900794 | 众数序列索引 20 | 完整消息 `[237,203,169,135,101]` |
| B | MP3 128k | `False` | 0.742063 | 未检测到 | `MISSING_TERMINATOR`，消息字节转换未执行 |

两条 MP3 都仍有 261 帧预测；预测值也包含零类帧，但跨重复块取众数后，21 个符号位置中没有终止符零类。官方代码接着对空的 `nonzero(ord_values == 0)` 取 `min`，触发异常；其宽泛异常捕获把异常统一折叠成 `status=False` / `Could not find message`。

因此失败属于**压缩后模型预测退化导致的协议解析失败**，不是 confidence 阈值导致拒绝，也不是消息字节重建代码出错。没有证据支持修改官方后处理即可修好；P2 没有针对单个失败样本调参或改模型。原始 confidence 虽高于 provisional presence 阈值，但没有成功消息候选，适配器仍判为 `UNKNOWN`，不会把官方 `status` 或单独的高分误作水印存在。

## 2. 适配器与 GUI

新增组件：

- [silentcipher_adapter.py](../../../app/silentcipher_adapter.py)：`embed(audio, message)`、`decode(received_audio)`、`detect(received_audio)`。消息严格为 5 字节；拒绝空/静音、非有限、超长及非法形状音频。官方 `status=True` 只表示其解码调用返回，不直接表示存在水印。
- `detect()` 使用独立可替换 `PresencePolicy`；当前 `0.680556` 标记为 `PRESENCE_CALIBRATION = PROVISIONAL`。无候选、低分或无效解析为 `UNKNOWN`；Python/模型异常为 `DECODE_ERROR`；只有有候选且分数过阈值才是 `IDENTIFIED`。API 没有预期消息、嵌入会话或 ground truth 参数。
- [v4_p2_gui.py](../../../experiments/v4_p2/prototype/v4_p2_gui.py)：独立 Gradio Blocks 页面，限定 12 秒/44.1 kHz 单声道演示输入；播放原音和水印音频，提供 WAV 下载、真实 MP3 128 kbps 往返及解码试听/下载，并以另一个文件上传控件执行盲检。不会自动把上传的正例状态传给检测函数。
- [v4_tempfiles.py](../../../app/v4_tempfiles.py)：每个任务单独目录、路径包含性检查、过期清理和进程退出清理。根目录若被外部缓存清理则在下次任务安全重建。
- [run_v4_p2_gui.sh](../../../experiments/v4_p2/prototype/run_v4_p2_gui.sh)：本地启动入口；源码和权重位置从环境变量传入，不写入仓库。

单进程模型单例、Torch CPU 线程上限默认 4、Gradio 队列单并发且队列上限 4。解码固定调用 `phase_shift_decoding=False`，不进行无界裁剪搜索。异常日志仅记录异常类名；普通界面不显示堆栈、本机路径或 FFmpeg stderr。

## 3. 实际 GUI 验收

使用 Gradio 4.44.1 本地服务和 `gradio_client` 通过实际页面注册的 `/embed`、`/mp3_roundtrip`、`/detect` 事件逐项调用；上传的是已用于 P1 的真实音乐片段，不是程序合成信号。服务绑定 `127.0.0.1`，未创建公开分享链接。

| 验收项 | 实测结果 |
|---|---|
| 上传、嵌入、播放/下载 WAV | 12 秒/44.1 kHz；消息 `123456789A`；文件生成且可下载；嵌入 SNR 48.88 dB |
| clean 独立上传盲检 | `IDENTIFIED`；消息正确；一致度 0.869048；检测 6.22 s |
| MP3 128 kbps 往返 | FFmpeg `libmp3lame` 编码和 PCM WAV 解码成功；MP3 与解码 WAV 均可下载/播放 |
| MP3 解码后独立盲检 | `UNKNOWN`；候选 `16C1DD0BB4`；一致度 0.345238；检测 5.93 s。错误候选未被接受 |
| 无水印原音负例 | `UNKNOWN`；候选 `175DD94249`；一致度 0.404762；检测 6.41 s。未被接受 |
| 非法消息 | 拒绝非 10 位十六进制输入；没有创建任务文件 |
| 无效音频 | 页面返回通用安全提示；不向用户暴露路径或 FFmpeg 错误 |
| 临时文件 | 工作期间 2 个私有 job、4 个输出文件；停止服务后根目录和其下文件均已清除 |

页面功能由真实 Gradio server/client 事件运行验证，没有进行人工浏览器截图验收。该范围不影响上表对嵌入/压缩/检测回调的 runtime 证据，但不把它表述成浏览器视觉 QA。

## 4. CPU、内存与依赖

- 运行环境：隔离 Python 3.12 venv、Torch 2.14.0 CPU、官方 SilentCipher 源码及已存在的 44.1 kHz checkpoint；不使用 GPU，也没有重下权重。
- 单例模型加载：最终运行记录约 0.04 s（不含 Python/Torch/Gradio 进程启动）。
- 该片段嵌入：3.40–4.59 s，报告记录值 4.59 s；波动受 CPU 状态影响。
- clean/MP3/negative 检测：分别约 6.22/5.93/6.41 s。
- GUI 进程 `/proc` 的 `VmHWM` 峰值为 1,551,720 kB，约 1.48 GiB。该值包括 Gradio、Torch 和模型；不是单个模型张量大小。
- FFmpeg 6.1.1 含 `libmp3lame`，实际链路通过。
- Gradio 原先未安装。经用户授权，按现有 requirements 锁定版本仅在隔离 venv 安装；该 venv 由 system-site-packages 复用 Torch。为适配 Python 3.12，临时安装清单省略 `audioop-lts`（该解释器自带 `audioop`）。venv 从约 241 MB 增至约 440 MB；系统盘快照可用空间约从 38 GiB 变为 37 GiB。没有修改 Conda/机器人环境。
- 由于 system-site-packages 共享底层包、Gradio 依赖又在 venv 中覆盖部分版本，pip 显示继承包依赖告警（包括 Mujoco 与 Transformers 的版本要求）。本地 MVP 实际 Gradio/Torch/FFmpeg 推理通过；该 venv 应专用于 V4 音频，不应用于机器人工作负载。上游 SilentCipher 自身声明的 Torch 版本上限与本轮可运行的 Torch 2.14 仍不一致，故这是工程可用组合，不是上游完整支持矩阵验证。

## 5. 与 V3 的差异及边界

P1 的冻结同源比较可作为参照：SilentCipher 为 40 bit / 12 s / 44.1 kHz，V3 为 8 bit / 6 s / 48 kHz。P1 测试集 MP3 精确恢复分别为 SilentCipher 10/12、V3 8/12；SilentCipher 平均约 4.38 s 嵌入、7.68 s 检测、1.58 GiB RSS，V3 约 0.064 s 嵌入、0.021 s 检测、代表性 RSS 140.5 MiB。容量、时长、采样率、存在判决语义均不同，样本小且音乐两首，不构成公平排名。

P2 只重用 V3/P1 报告数字，没有重跑 V3，也没有改动 V3 算法、历史数据或线上 Render 服务。本轮现场只验证一段音乐；P1 语音和环境声结果仍是此前的小规模证据，不是 P2 新测结果。

## 6. 已知限制与建议

1. 当前存在性阈值只来自 P1 小开发集的探索性分离。P2 一个 clean 正例和一个负例只能验证链路行为，不能估计 FAR/FRR；`0.680556` 必须持续显示 provisional。
2. 真实 MP3 输入/输出通路能运行，但音乐 MP3 正例未恢复消息。不能把“压缩按钮工作”写成“MP3 鲁棒性通过”。
3. SilentCipher 权重许可是否允许公开再分发仍未确认；课程交付应引用官方来源，并避免把权重提交到 GitHub。
4. 临时工作目录由 16 MiB 上传上限和 60 秒音频上限约束，模型时延数秒、峰值约 1.48 GiB，不适合多并发或低延迟服务。
5. 本地环境未验证 AAC、浏览器视觉 QA、长音频、重采样/混响/平台转码或 phase-shift 裁剪检测。
6. 下一步先做有限的同一适配器冒烟检查：speech/music/environment 各取一个已授权来源，分别跑 clean 和 MP3，核对解码候选、终止符与 provisional 判决；随后再决定 SilentCipher 能否维持主候选或需保留 V3 回退。不要以单条音乐样本调阈值。
7. 完整课程系统建议维持双后端：V3 冻结 DSP 基线 + SilentCipher 神经候选；共用明确预处理、STFT/波形、FFmpeg 信道、SNR/LSD、试听和盲检页面。用显式后端选择而非静默切换；神经后端保持单 worker、独立 presence policy 和拒绝状态展示。

## 7. 冻结保护与复现文件

- P0/P1 报告、P1 `RESULTS.json`、`CROP_CHECK.json` 和 `scripts/v4_p1_validate.py` 本轮未修改；复核时记录了它们的 SHA-256。
- V3 位于独立冻结工作区，本轮未写入 V3 或 Render。
- 只新增 V4-P2 适配器、诊断、GUI、测试、启动脚本和本报告；没有 GitHub 推送、没有提交权重/音频/凭证。
- 测试使用 Python 标准库 `unittest`，3 个测试文件共 9 项通过：适配器状态与输入、诊断终止符识别、临时目录隔离/清理、GUI 回调及真实 FFmpeg MP3 路径。
- 本地启动需要使用已有 Python 3.12 venv，并设置 `SILENTCIPHER_SOURCE_ROOT`、`SILENTCIPHER_MODEL_DIR`（指向既有官方源码与 44.1 kHz 模型目录），然后运行 `scripts/run_v4_p2_gui.sh`。启动器默认 `python3`，也可设置 `V4_P2_PYTHON`。
