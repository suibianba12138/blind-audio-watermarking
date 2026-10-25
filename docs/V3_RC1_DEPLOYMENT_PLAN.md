# V3-RC1 部署计划（未执行）

## 当前决策

`RENDER_DEPLOYMENT_READINESS = NO-GO`，`PUSH_STATUS = NOT_PERFORMED`。

本轮没有 push、merge、Render 部署、公开 share URL 或生产服务变更。

## 进入下一轮前必须完成

1. 在本分支增加可审查的 V3 container descriptor：复制已审计的非 root、FFmpeg、PORT、queue 和 16 MiB 结构，但入口必须是 V3 集成应用；不得把 Legacy image 当成 V3 image。
2. 在本地 Docker 中 build/run V3 image，验证 `0.0.0.0` 内部监听、`PORT` 映射、非 root、FFmpeg 和容器内真实 V3 MP3 流程。
3. 完成真实浏览器清单中的上传、下载、重新上传、UNKNOWN、刷新和双会话隔离检查。
4. 再检查容器内输入大小、30 秒边界、超时、队列、TTL 和 Gradio cache 生命周期。
5. 保留 Legacy Course V2 作为回退入口；生产切换必须可回退到当前 Legacy 版本。
6. 由用户明确批准后，才允许 remote push、merge 或 Render 操作。

## 回退方案

- 不替换当前 Legacy 入口。
- V3 仅作为独立入口或 feature flag 提供。
- V3 失败时停止 V3 路由，保留 Legacy Course V2 和其历史指标。
- 不修改冻结的 Course V2、V3 算法参数、REAL_TOP32 map 或历史实验数据。

## 运行时约束

建议部署配置：非 root 用户、内部 `0.0.0.0:$PORT`、Gradio `max_file_size=16mb`、
单并发、有限队列、FFmpeg 明确超时、session TTL 和临时目录清理。正式上线前还需要
真实平台资源验证；本地 Docker 参考结果不能替代该验证。
