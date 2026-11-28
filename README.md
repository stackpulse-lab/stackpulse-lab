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
| **[LeakPulse](https://github.com/stackpulse-lab/leakpulse)** | 零依赖密钥泄露扫描器：工作区 / 暂存区 / 提交历史，覆盖 GitHub/OpenAI 与 DeepSeek、阿里云、腾讯云、飞书/企微/钉钉、爱发电等 28 条规则；零配置 GitHub Action、pre-commit 钩子、SARIF（Code Scanning）/ HTML 审计报告，以及只对新增密钥报错的基线模式 | ✅ `v0.5.0` |
| **[CronPulse](https://github.com/stackpulse-lab/cronpulse)** | Cron/systemd 定时体检：表达式解释、DST 边界检测、Quartz 方言拦截、crontab/systemd 清单漂移检查 | ✅ `v0.6.1` |
| **PortPulse** | 端口占用清单与冲突定位，替代记不住的 `ss` 参数组合 | 🧪 规划中 |
| **LogPulse** | JSON/文本日志的流式过滤、字段提取与慢请求归因 | 🧪 规划中 |

> 规划中的项目会按周迭代发布；只把真正跑通、有测试的东西标成「已发布」。

### 文章

我们把真实的踩坑过程写成可复现手册：命令、终端输出、退出码齐全，示例凭据全部在运行时生成。

| 日期 | 文章 | 主题 |
| --- | --- | --- |
| 2026-11-27 | [密钥泄露后的 10 分钟](articles/secret-leak-10min.zh.md) | 轮换优先、历史取证、pre-commit/CI 门禁、复盘清单 |
| 2026-11-27 | [存量仓库接入密钥扫描：基线模式 10 分钟落地](articles/legacy-repo-baseline.zh.md) | 基线指纹、增量 CI、轮换与路径边界、运维约定 |
| 2026-11-28 | [定时任务没跑：DST 缺 02:30 与 systemd timer 清单漂移排查实录](articles/cronpulse-dst-timer-drift.zh.md) | DST gap/overlap、真实偏移、timer 清单漂移、退出码分级 |

更多见 [`articles/`](articles/)，英文版本在每篇文章内互链。

### 服务：CI 密钥防线 + 定时任务体检

给 5–50 人工程团队的一次性「止血 + 对账」交付包：用 LeakPulse 把密钥挡在提交之前，用 CronPulse 找出悄悄失灵的 cron / systemd timer。

- **免费**：交付模板（信息收集表、体检清单、报告模板、清单样例）随仓库开放，MIT。
- **付费**：轻体检 499 CNY / 次，落地陪跑 1500 CNY 起（试运营价）。
- **边界**：只读审计，不接触真实凭据、不远程登录生产机、不代管密钥、不改写 Git 历史。

详见 [交付包说明与模板](offers/ci-secrets-cron-health/README.md)。

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
| **[LeakPulse](https://github.com/stackpulse-lab/leakpulse)** | Dependency-free secret scanner for working trees, staged changes and git history — 28 rules including DeepSeek, Aliyun, Tencent Cloud, Feishu/WeCom/DingTalk webhooks and Afdian tokens; zero-config GitHub Action, pre-commit hooks, SARIF (code scanning) / HTML audit reports, and baseline mode that fails only on new secrets | ✅ `v0.5.0` |
| **[CronPulse](https://github.com/stackpulse-lab/cronpulse)** | Cron & systemd schedule guard: explain expressions, DST gap/overlap detection, crontab & systemd timer drift checks | ✅ `v0.6.1` |
| **PortPulse** | Listener inventory and port-conflict diagnostics without memorizing `ss` flags | 🧪 Planned |
| **LogPulse** | Streaming filter, field extraction and slow-request attribution for JSON/text logs | 🧪 Planned |

> Planned projects ship weekly. Nothing is marked “released” until it runs and has tests.

### Articles

Real incident write-ups with reproducible commands, terminal output and exit codes. Demo credentials are generated at runtime.

| Date | Article | Topic |
| --- | --- | --- |
| 2026-11-27 | [The first 10 minutes after a secret leak](articles/secret-leak-10min.en.md) | Rotate first, history forensics, pre-commit/CI gates, postmortem checklist |
| 2026-11-27 | [Adopting a secret scanner in a legacy repo](articles/legacy-repo-baseline.en.md) | Baseline fingerprints, incremental CI, rotation/path boundaries, operating rules |
| 2026-11-28 | [When the schedule did not run: DST gaps and systemd timer drift](articles/cronpulse-dst-timer-drift.en.md) | DST gap/overlap, real offsets, timer inventory drift, exit-code routing |

See [`articles/`](articles/) for the index; each article links to its Chinese/English counterpart.

### Service: CI secret gates + schedule health check

A fixed-scope "stop the bleeding + reconcile the schedule" package for teams of 5–50 engineers: LeakPulse blocks secrets before commit, CronPulse finds cron jobs and systemd timers that quietly stopped working.

- **Free**: every delivery template (intake form, audit checklist, report template, manifest examples) is in the repo under MIT.
- **Paid**: light audit at 499 CNY, landing support from 1500 CNY (introductory pricing).
- **Boundaries**: read-only audit; we never handle real credentials, log in to production, manage secrets, or rewrite Git history.

See the [offer page and templates](offers/ci-secrets-cron-health/README.md).

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
