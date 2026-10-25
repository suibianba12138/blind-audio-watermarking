# V3-RC1 Docker 与资源验收报告

## 结论

`DOCKER_RESOURCE_GATE = PARTIAL`。

现有 public staging 的 Legacy Docker 架构可以本地构建和运行，但当前
`feat/v3-8bit-integration` 没有 Dockerfile、compose 文件、Render blueprint 或 V3
container entrypoint。因此不能把 Legacy 容器证据升级为 V3 Docker PASS。

## 已检查配置

当前 V3 分支的应用层配置：

- Python 本地隔离运行时：`3.13.5`；依赖锁定 Gradio `4.44.1`、gradio-client `1.3.0`。
- FFmpeg 本机：`6.1.1`；V3 使用真实 `libmp3lame` 128 kbps。
- 输入大小：代码和 Gradio launcher 均为 `16 MiB`。
- 解码时长：最长 `30 s`；V3 算法验证仍是固定 `6 s`。
- FFmpeg 超时：`120 s`；盲检测子进程超时：`180 s`。
- Gradio：单任务并发 `1`，队列上限 `4`，不创建 share URL。
- Session TTL：V3 与 Legacy 均为 `3600 s`；路径遍历、符号链接和过期 session 有拒绝/清理逻辑。
- 本地 V3 launcher：`127.0.0.1`；不是可直接用于 Render 的监听配置。

## Legacy 容器参考验收

使用未修改的 `/home/nsk/blind-audio-watermarking-public-staging/Dockerfile`：

```bash
docker build -f /home/nsk/blind-audio-watermarking-public-staging/Dockerfile \
  -t blind-audio-watermarking:rc1-legacy-audit \
  /home/nsk/blind-audio-watermarking-public-staging
docker run --rm --detach --name blind-audio-rc1-legacy \
  -p 127.0.0.1:8786:7860 blind-audio-watermarking:rc1-legacy-audit
```

实际结果：

- Build：PASS；镜像未 push。
- HTTP `/`：`200`。
- 用户：`uid=10001(demo)`，非 root。
- 容器 Python：`3.11.17`。
- 容器 FFmpeg：`7.1.5`，可执行。
- 暴露端口：`7860/tcp`；本地映射 `127.0.0.1:8786`。
- 短时 `docker stats`：约 `296.5 MiB`，仅为 Legacy 空闲/启动参考，不是 Render Free 保证。
- 该镜像 CMD 为 `app.hosted`，没有复制当前 V3 `gradio_v3_app.py`、V3 API 和 V3 integration callbacks。

容器已在检查后停止。当前环境最初的 Docker daemon socket 受沙箱限制，授权后才完成
上述 Legacy 参考检查；这不改变 V3 descriptor 缺失这一事实。

## 未建立的门禁

- `V3_DOCKER_BUILD = BLOCKED`：当前分支没有可构建的 V3 Docker context。
- `V3_CONTAINER_BROWSER = NOT_ESTABLISHED`：没有 V3 容器可供浏览器访问。
- `RENDER_RESOURCE_COMPATIBILITY = NOT_ESTABLISHED`：本地 Legacy stats 不能代表 Render Free 的 CPU、内存、冷启动和临时盘行为。
- Gradio 自身 `/tmp/gradio` cache 的 provider-level 清理没有独立 TTL 证据；应用 session artifact 已由 `SessionStore` 约束和清理。
