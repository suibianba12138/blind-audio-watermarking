# V3-RC1 浏览器人工验收清单

基线：`feat/v3-8bit-integration @ abd3795`。本轮只验证展示与部署边界，未修改
V3 8-bit Soft-Code、QIM、码本、strength、threshold、selector 或历史实验。

## 启动命令

```bash
cd /home/nsk/blind-audio-watermarking-v3-p0
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
  GRADIO_ANALYTICS_ENABLED=False GRADIO_SERVER_PORT=7865 \
  PYTHONPATH=src:scripts:. \
  /tmp/v3-p3-gradio-venv2/bin/python gradio_v3_app.py
```

V3/Legacy 集成页只绑定 `127.0.0.1`，不创建 Gradio share URL。独立 Legacy 入口为：

```bash
PYTHONPATH=src:scripts:. /tmp/v3-p3-gradio-venv2/bin/python gradio_app.py
```

## 自动化但非浏览器证据

| 检查 | 结果 | 证据 |
|---|---|---|
| HTTP `/`、`/config` | PASS | localhost HTTP 200；Gradio `4.44.1` |
| V3 上传/消息 173/嵌入 | PASS | pinned `gradio_client` callback |
| 真实 MP3 128 kbps | PASS | 返回文件后缀 `.mp3`，FFmpeg 流程完成 |
| MP3 重新上传盲检测 | PASS | `DETECTED: 173` |
| 干净音频检测 | PASS | `UNKNOWN / NO VALID WATERMARK` |
| V3 → Legacy 模式切换 | PASS | `_toggle_mode` callback |
| Legacy UESTC-003 | PASS | 嵌入、MP3、盲检测返回 `UESTC-003` |

这些结果是 HTTP/client smoke，不等同于人工浏览器验收。

## 人工浏览器步骤

在可控浏览器中逐项打勾，并保存截图或操作记录：

| # | 操作 | 期望结果 | 当前状态 |
|---:|---|---|---|
| 1 | 上传真实 WAV/音频 | 页面接受文件并可试听 | NOT_ESTABLISHED |
| 2 | 输入可变消息，例如 `173`，点击 V3 embed | 输出原始/水印 WAV 可试听、可下载 | NOT_ESTABLISHED |
| 3 | 下载水印 WAV 后重新上传 | WAV 可解码，哈希/采样率记录可核对 | NOT_ESTABLISHED |
| 4 | 点击真实 MP3 128 kbps | MP3 文件可下载、可播放 | NOT_ESTABLISHED |
| 5 | 将 MP3 下载文件重新上传到 Received audio | 文件保持 MP3，不被 Audio 组件替换为 WAV | NOT_ESTABLISHED |
| 6 | 点击 V3 blind detect | 显示 `DETECTED: 173`、score、threshold、margin、时长和采样率 | NOT_ESTABLISHED |
| 7 | 上传未嵌入音频 | 显示 `UNKNOWN / NO VALID WATERMARK` | NOT_ESTABLISHED |
| 8 | 切换 Legacy Course V2 | Legacy 身份、6/15/30 秒控件显示且功能回归 | NOT_ESTABLISHED |
| 9 | 错误格式、超过 16 MiB、超过 30 秒、过期 state | 明确错误或 UNKNOWN，不泄露其他会话文件 | NOT_ESTABLISHED |
| 10 | 刷新、重复操作、两个浏览器会话 | 状态隔离；不能读取另一会话产物 | NOT_ESTABLISHED |

## 浏览器阻塞

本次尝试连接本地浏览器时，浏览器后端返回 `No browser is available`，可用列表为
空。因此本文件不把 client smoke 写成 Browser PASS。需要在有可控浏览器的环境中
重新执行上表；在此之前 `V3_BROWSER_ACCEPTANCE = NOT_ESTABLISHED`。
