# Public Release P3 — Release Blocker Resolution

本文件记录本地公开候选版本的发布门禁。当前只完成本地准备，不 push、不创建
GitHub Release、不部署网站。

```makefile
CODE_OWNERSHIP = PASS
THIRD_PARTY_CODE = PASS
MIT_LICENSE = MIT_READY
DATA_LICENSE = PASS_METADATA_ONLY
GIT_HISTORY_PRIVACY = BLOCKED_PENDING_VERIFIED_EMAIL
PUBLIC_FILE_SCAN = PASS

STANDALONE_INSTALL = PASS
CORE_TESTS = PASS
MP3_TEST = PASS
GRADIO_TEST = PASS

PUBLIC_RELEASE_READY = CONDITIONAL
STAGING_DIRECTORY = blind-audio-watermarking-public-staging
NEXT_ACTION = Configure and verify the GitHub privacy-protected commit email, create the first fresh commit, then repeat the full release gate before any push.
```

## 权属与第三方材料

项目维护者已确认当前公开版本主要是其拥有发布权限的自有项目代码，因此项目
源码和公开包装可以使用 MIT License。源码扫描未发现复制的第三方源文件、第三方
图片、第三方音频或随仓库分发的依赖源码。NumPy、SciPy、pytest、Gradio、FFmpeg
等外部依赖保留各自许可证，不被本项目 MIT 文本覆盖。

必要的学术引用保留在结果和方法文档中；项目不在 README 中添加人员分工或开发
方式章节。

## 数据来源

冻结的校准/验证记录使用外部 MUSAN / OpenSLR SLR17 录音。公开版本只保留聚合
统计结果，不包含 MUSAN 原始音频、压缩包、逐录音 source manifest 或私有路径。
OpenSLR 将 SLR17 标为 CC BY 4.0；本版本保留数据集引用，但不授予原始录音再
分发权。结果文档明确区分冻结 provenance 与本地 smoke test。

## Git 隐私

staging 使用全新 Git 目录，不复制旧 `.git` 和旧提交历史。首次提交尚未创建，
因为当前环境无法核对 GitHub 账户的实际已验证隐私保护邮箱。不得推测 noreply
地址；提交前必须同时核对 Author/Committer name 和 email，并确认使用 GitHub
账户已验证且隐私保护的邮箱。
