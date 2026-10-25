# Blind Audio Watermarking V3-RC1 Release Acceptance

基线：`feat/v3-8bit-integration @ abd3795c574d7ed28fefe4d36168f9a701537735`。

本轮只做 release-candidate 工程验收和部署/安全层修复。冻结算法文件及 V3-P2-V、
P3 历史结果没有修改；冻结文件 diff 为空。

## 状态

```makefile
V3_RC1_STATUS = CONDITIONAL
V3_BROWSER_ACCEPTANCE = NOT_ESTABLISHED
MP3_DOWNLOAD_REUPLOAD = PASS
V3_LEGACY_REGRESSION = PASS
SESSION_ISOLATION = PASS_LOCAL_BROWSER_UNVERIFIED
DOCKER_RESOURCE_GATE = PARTIAL
AUDIO_QUALITY_SCREENING = NOT_ESTABLISHED
GIT_INTEGRATION_READINESS = CONDITIONAL
RENDER_DEPLOYMENT_READINESS = NO-GO
```

## 已通过证据

- 全部回归：`110 passed, 1 skipped`；唯一 skip 是默认环境未安装 Gradio 的构建测试。隔离 Gradio 运行时已另行通过 HTTP/client smoke。
- `compileall`：PASS。
- `git diff --check`：PASS。
- V3 直接 API 和独立 detector：保留 P3 冻结结果；本轮 client smoke 用消息 `173`。
- WAV 重读：48 kHz、288000 samples，最大绝对差约 `1.49e-8`。
- MP3：`codec=mp3`、mono、48 kHz、`128000 bps`；原始 MP3 字节与解码 PCM 分开验证。
- 下载/重新上传：MP3 作为 `gr.File` 传输，盲检测 `DETECTED: 173`；干净 WAV 为 `UNKNOWN`。
- Legacy UESTC-003：真实 FFmpeg MP3 后，6/15/30 秒分别使用 1/2/5 个时间块并正确识别。
- Legacy 无水印控制：6 秒 MP3 返回 `UNKNOWN`。
- Session：V3/Legacy 均使用 opaque session ID、TTL 3600 s、路径边界和失败清理；客户端不能直接指定绝对路径。
- 输入：16 MiB 和 30 秒边界已加入回归；Gradio launcher 声明 `16mb`、单并发、队列上限 4。
- Legacy Docker 参考 image：build/run、HTTP、非 root、FFmpeg 和端口检查通过。

## 阻塞与限制

1. 当前 V3 分支没有 Dockerfile/compose/Render blueprint；现有 Docker 只属于 Legacy，
   因此 V3 Docker/Render 门禁未通过。
2. 当前环境没有可控浏览器后端；浏览器人工清单中的点击、下载、刷新和双会话操作
   未建立证据。Gradio HTTP/client smoke 不能冒充 browser acceptance。
3. 没有正式人工感知质量实验；`AUDIO_QUALITY_SCREENING` 仍是
   `NOT_ESTABLISHED`，不能声称不可感知。
4. Gradio 播放组件出现自动 int32→16-bit 转换 warning；V3 检测输入使用独立 MP3
   `gr.File`，该 warning 未被当作检测输入，但应在浏览器/试听阶段继续观察。
5. 未 fetch 远程 main；本报告使用已有 `origin/main` ref 做差异审计，不声称远程最新。

## 交付命令

```bash
PYTHONPATH=src:scripts:. PYTEST_ADDOPTS='-p no:cacheprovider' pytest -q
PYTHONPYCACHEPREFIX=/tmp/v3-rc1-pyc PYTHONPATH=src:scripts:. python -m compileall -q src app scripts tests
git diff --check
```

下一步不是继续调算法，而是补齐 V3 容器描述、完成真实浏览器清单，再由用户决定是否
允许 remote push/merge/deploy。
