# Articles · 技术文章

实战向的运维 / 开发效率文章，命令与输出均可复现。示例凭据全部为运行时生成的假值。

Practical ops and developer-tooling write-ups with reproducible commands and outputs. All demo credentials are fake values generated at runtime.

| 日期 | 中文 | English | 主题 |
| --- | --- | --- | --- |
| 2026-11-27 | [密钥泄露后的 10 分钟](secret-leak-10min.zh.md) | [The first 10 minutes after a secret leak](secret-leak-10min.en.md) | 应急响应、历史取证、pre-commit/CI 门禁 |
| 2026-11-27 | [存量仓库接入密钥扫描：基线模式 10 分钟落地](legacy-repo-baseline.zh.md) | [Adopting a secret scanner in a legacy repo](legacy-repo-baseline.en.md) | 基线指纹、增量 CI、轮换与路径边界、运维约定 |
| 2026-11-28 | [定时任务没跑：DST 缺 02:30 与 systemd timer 清单漂移排查实录](cronpulse-dst-timer-drift.zh.md) | [When the schedule did not run: DST gaps and systemd timer drift](cronpulse-dst-timer-drift.en.md) | DST gap/overlap、真实偏移、timer 清单漂移、退出码分级 |

## 约定 / Conventions

- 每篇文章给出可复制命令、真实终端输出与退出码。
- 不包含任何可用的密钥、Token 或 Webhook；演示值在过程中生成。
- 工具遵循 MIT、零第三方依赖、本地运行（不联网、不上传）。
- 勘误与选题建议请开 Issue：<https://github.com/stackpulse-lab/stackpulse-lab/issues>。
