# CI 密钥防线 + 定时任务体检 · 开箱即用交付包

> 给 5–50 人工程团队的一次性「止血 + 对账」服务：把密钥泄露挡在提交之前，把悄悄失灵的 cron / systemd timer 找出来。
> A one-off "stop the bleeding + reconcile the schedule" package for teams of 5–50 engineers.

- 适用对象：已有生产仓库与 Linux 主机、但没有专职安全/运维的中小团队
- 工具基础（MIT、零依赖、可离线运行）：[LeakPulse](https://github.com/stackpulse-lab/leakpulse) `pip install leakpulse`、[CronPulse](https://github.com/stackpulse-lab/cronpulse) `pip install cronpulse-cli`
- 交付形态：**只读审计 + 客户自行执行变更**；我们不接触生产凭据、不代管密钥、不远程登录客户生产机
- 状态：试运营（价格与档位需管理员在爱发电上架后生效）

---

## 1. 解决什么问题

两类事故的共同点是「出事前没人看得见」：

| 症状 | 真实原因 | 对应能力 |
| --- | --- | --- |
| 密钥进了公开仓库，几小时后才被扫描器/好心人告知 | 没有 pre-commit / CI 门禁，或历史命中太多导致检查被关掉 | LeakPulse 历史扫描 + 基线模式 + Action |
| 备份任务「昨天还在跑」，今天没跑 | DST 让 `30 2 * * *` 当天不存在；或 timer 被改名/改时间 | CronPulse `next` / `check` / `drift` / `timer-drift` |
| 任务重复执行、账单翻倍 | 秋季 DST overlap、重复 `OnCalendar=`、两台机器各跑一份 | CronPulse DST `ambiguous` 输出、漂移报告 `duplicates` |
| 想接入检查，但一开就几百条红 | 存量仓库历史 fixture 与已轮换密钥 | 基线指纹：只对新增命中报错 |

## 2. 三档交付（试运营价）

| 档位 | 内容 | 价格 | 交付周期 |
| --- | --- | --- | --- |
| **A. 自助包** | 本目录全部模板（信息表 / 体检清单 / 报告模板 / 清单样例）+ 对应开源工具 | **免费**（MIT） | 即时 |
| **B. 轻体检** | 1 个仓库的密钥防线 + 1 台主机的定时任务体检；含书面报告与修复清单 | **499 CNY / 次** | 5 个工作日 |
| **C. 落地陪跑** | 最多 3 个仓库 + CI 工作流改造建议 + 基线评审 + 30 天内 2 次邮件答疑 | **1500 CNY 起** | 10 个工作日 |

> 价格是试运营报价，用于验证需求；正式上架以爱发电商品页为准。开源工具本身永远免费，不因付费档位而阉割。

## 3. 开源核心 vs 付费增值（边界写死）

| 类别 | 内容 | 许可 / 归属 |
| --- | --- | --- |
| **开源核心（永久免费）** | LeakPulse / CronPulse 全部 CLI 能力、GitHub Action、pre-commit 钩子、SARIF/HTML 报告、文档与文章 | MIT，可商用、可修改、可分发 |
| **免费模板（本目录）** | 信息收集表、体检清单、报告模板、crontab / timer 清单样例 | MIT，可自用与二次分发（保留版权声明） |
| **付费增值** | 针对客户仓库/主机的**执行与判断**：跑扫描、分级、基线评审、漂移对账、修复顺序建议、书面报告、答疑 | 服务成果归客户；不含任何密钥 |
| **付费定制** | 客户自有规则的私有分支、内部系统对接脚本、一次性迁移工具 | 单独约定；默认不回灌上游 |

明确不做：

- 不做渗透测试、不做合规认证（等保/SOC2）背书；
- 不接收、不存储、不代管任何真实密钥或生产凭据；
- 不远程登录客户生产机，不替客户执行破坏性变更；
- 不 merge 外部 PR，不改写客户 Git 历史（历史重写始终由客户自己决策与执行）。

## 4. 交付流程（7 步）

1. **信息收集**：客户填写 [`templates/intake.yml`](templates/intake.yml)（只填仓库地址/主机概况，**禁止填密钥**）。
2. **环境确认**：确认 Python ≥ 3.9、git 可用、是否有 CI；工具在客户侧或隔离副本上运行。
3. **密钥防线**：`leakpulse scan`（工作区 / 暂存区 / 历史）→ 分级 → 生成基线 → 给出 pre-commit + CI 接入方案。
4. **定时任务体检**：`cronpulse next/check/drift/timer-drift` → 列出永不触发、DST 缺口、重复与漂移项。
5. **证据整理**：所有结论附命令、退出码与脱敏输出（见 [`templates/delivery-report.md`](templates/delivery-report.md)）。
6. **客户执行**：按清单自行轮换密钥、改定时任务、提交基线；我们只做复核。
7. **验收**：以「新增 1 条测试命中能被 CI 拦住」和「漂移清单复跑退出码为 0」为通过标准。

## 5. 验收标准（可验证，不靠口头）

- 密钥防线：在临时分支放入一个**运行时生成**的假 Token，`pre-commit` 或 CI **必须失败**；删除后恢复通过。
- 基线：`leakpulse scan --baseline <file>` 对存量命中退出 `0`，对新增命中退出 `1`。
- 定时任务：`cronpulse drift` / `timer-drift` 修复后退出 `0`；修复前退出 `4` 并明确列出 `missing / unexpected / changed`。
- 报告：每条发现都有「命令 + 退出码 + 脱敏片段 + 建议动作 + 责任方」。
- 零泄露：交付物中不含任何真实密钥；示例值均为运行时生成的假值。

## 6. 常用命令卡片

```bash
# 安装（PyPI）
pip install leakpulse cronpulse-cli

# 密钥：历史取证 → 基线 → 增量门禁
leakpulse scan . --history 50 --fail-on high
leakpulse scan . --history 50 --write-baseline .leakpulse-baseline.json
leakpulse scan . --baseline .leakpulse-baseline.json --fail-on high

# 定时任务：表达式 → 未来触发 → 永不触发 → 清单漂移
cronpulse next "30 2 * * *" --tz Asia/Shanghai -n 3
cronpulse check "0 0 30 2 *"
cronpulse drift crontab.txt --expect templates/cron-manifest.example.json
cronpulse timer-drift /etc/systemd/system --expect templates/timers.example.json
```

退出码约定：`0` 通过，`1` 扫描命中，`2` 输入非法/不可读，`3` 永不触发，`4` 漂移或告警。
注意管道会吞掉退出码，脚本里用 `set -o pipefail` 或 `PIPESTATUS[0]`。

## 7. 参考材料

- [密钥泄露后的 10 分钟](../../articles/secret-leak-10min.zh.md)
- [存量仓库接入密钥扫描：基线模式](../../articles/legacy-repo-baseline.zh.md)
- [定时任务没跑：DST 与 systemd timer 漂移](../../articles/cronpulse-dst-timer-drift.zh.md)
- [LeakPulse 基线文档](https://github.com/stackpulse-lab/leakpulse/blob/main/docs/baseline.md)

## 8. English summary

A fixed-scope engagement for small teams that have production repos and Linux hosts but no dedicated security/ops engineer.

- **Free (MIT)**: the open-source tools plus every template in this directory.
- **Light audit — 499 CNY**: one repository and one host; written findings with commands, exit codes and redacted output.
- **Landing support — from 1500 CNY**: up to three repositories, CI workflow guidance, baseline review, two Q&A rounds within 30 days.
- **Never included**: handling real credentials, production access, penetration testing, compliance certification, or rewriting customer Git history.
- **Acceptance**: a runtime-generated fake token must be blocked by the gate, and the drift check must exit `0` after remediation (`4` before).

Contact: open an issue titled “Cooperation” in any StackPulse Lab repository.
