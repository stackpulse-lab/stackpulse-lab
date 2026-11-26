# StackPulse Lab · 栈脉工坊

> 小而锋利、零依赖、可审计的开发者与运维工具。
> Small, sharp, dependency-free tools for developers and operators.

[![GitHub](https://img.shields.io/badge/GitHub-stackpulse--lab-181717?logo=github)](https://github.com/stackpulse-lab)
[![License](https://img.shields.io/badge/license-MIT-2ea44f)](https://github.com/stackpulse-lab/leakpulse/blob/main/LICENSE)
[![Made with Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## 中文

### 我们是谁

**栈脉工坊（StackPulse Lab）** 是一个专注 **开发者效率** 与 **运维可靠性** 的独立工具实验室。

我们相信：真正好用的工具应该**小而专注**——装得上、看得懂、改得动，不把半个互联网塞进依赖树。每个项目都遵循同一套标准：

- **零/极少依赖**：只用标准库能跑，审计成本低，离线可用。
- **默认安全**：不联网、不上传、不收集遥测；敏感信息在输出中自动脱敏。
- **可测试**：自带单元测试与 CI，行为可验证，不靠口头承诺。
- **MIT 协议**：自由商用、修改、分发，只需保留版权声明。

### 我们在做什么

围绕日常开发与运维中最琐碎、最容易出事的环节，提供一板一眼的小工具：

| 项目 | 用途 | 状态 |
| --- | --- | --- |
| **[LeakPulse](https://github.com/stackpulse-lab/leakpulse)** | 零依赖密钥泄露扫描器：工作区 / 暂存区 / 提交历史，覆盖 GitHub/OpenAI 与 DeepSeek、阿里云、腾讯云、飞书/企微/钉钉、爱发电等 28 条规则；零配置 GitHub Action、pre-commit 钩子，以及 SARIF（Code Scanning）/ HTML 审计报告 | ✅ `v0.4.0` |
| **[CronPulse](https://github.com/stackpulse-lab/cronpulse)** | Cron/systemd 定时体检：表达式解释、DST 边界检测、Quartz 方言拦截、crontab/systemd 清单漂移检查 | ✅ `v0.6.1` |
| **PortPulse** | 端口占用清单与冲突定位，替代记不住的 `ss` 参数组合 | 🧪 规划中 |
| **LogPulse** | JSON/文本日志的流式过滤、字段提取与慢请求归因 | 🧪 规划中 |

> 规划中的项目会按周迭代发布；只把真正跑通、有测试的东西标成「已发布」。

### 为什么值得关注

- 每个仓库都有**完整 README、变更日志与单元测试**，不是一次性脚本。
- 工具面向 CI / pre-commit / cron 等**真实工作流**，而不是演示 demo。
- 问题与需求直接开 Issue，作者本人维护。

### 支持我们

如果这些工具替你省下了时间，欢迎通过 [爱发电](https://afdian.com/a/stackpulse-lab) 请作者喝杯咖啡。
赞助不会影响开源版本的 MIT 许可与功能完整性。

### 联系

- Issue：对应仓库的 Issues 页（推荐）
- 商务 / 定制脚本：在任意仓库开 Issue 并标注「合作」（Cooperation）

---

## English

### Who we are

**StackPulse Lab** is an independent lab building **developer productivity** and **ops reliability** tools.

We believe good tools should be **small and focused** — installable, readable, hackable, without dragging half the internet into your dependency tree. Every project follows the same contract:

- **Zero / minimal dependencies** — standard library first; low audit cost, works offline.
- **Secure by default** — no network calls, no uploads, no telemetry; secrets are redacted in output.
- **Tested** — unit tests and CI in every repo; behavior you can verify.
- **MIT licensed** — free to use commercially, modify and redistribute.

### What we build

Small, sharp utilities for the fiddly parts of daily development and operations:

| Project | What it does | Status |
| --- | --- | --- |
| **[LeakPulse](https://github.com/stackpulse-lab/leakpulse)** | Dependency-free secret scanner for working trees, staged changes and git history — 28 rules including DeepSeek, Aliyun, Tencent Cloud, Feishu/WeCom/DingTalk webhooks and Afdian tokens; zero-config GitHub Action, pre-commit hooks, and SARIF (code scanning) / HTML audit reports | ✅ `v0.4.0` |
| **[CronPulse](https://github.com/stackpulse-lab/cronpulse)** | Cron & systemd schedule guard: explain expressions, DST gap/overlap detection, crontab & systemd timer drift checks | ✅ `v0.6.1` |
| **PortPulse** | Listener inventory and port-conflict diagnostics without memorizing `ss` flags | 🧪 Planned |
| **LogPulse** | Streaming filter, field extraction and slow-request attribution for JSON/text logs | 🧪 Planned |

> Planned projects ship weekly. Nothing is marked “released” until it runs and has tests.

### Why follow

- Every repo ships a **real README, changelog and unit tests** — not a throwaway script.
- Built for **actual workflows**: CI, pre-commit hooks, cron and systemd.
- Issues are triaged and fixed by the maintainer.

### Support

If a tool saved you time, you can [buy the author a coffee](https://afdian.com/a/stackpulse-lab).
Sponsorship never changes the MIT license or removes features from the open-source edition.

### Contact

- Issues: the Issues tab of the relevant repository (preferred)
- Business / custom automation: open an issue titled “Cooperation” in any repository

---

<sub>© 2026 StackPulse Lab · 栈脉工坊 · Built with care, shipped with tests.</sub>
