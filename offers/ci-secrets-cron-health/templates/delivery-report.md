# 交付报告模板 / Delivery report template

> 复制本文件为 `report-<客户>-<日期>.md` 后填写。所有「证据」栏必须是**实际运行**的命令与
> 脱敏输出；未运行的项写「未验证」，不要留空，也不要推测。

## 基本信息

| 项 | 值 |
| --- | --- |
| 客户 | `<客户名称>` |
| 档位 | `<B_light_audit / C_landing_support>` |
| 审计范围 | `<仓库数> 个仓库 / <主机角色> 台主机 |
| 执行时间 | `<YYYY-MM-DD HH:MM TZ>` |
| 工具版本 | `leakpulse <x.y.z>`、`cronpulse <x.y.z>` |
| 执行者 | `StackPulse Lab` |
| 报告保留期 | `<如：交付后 30 天删除>` |

## 结论摘要（给不看细节的人）

- 密钥防线：`<共 N 条历史命中，其中 high H 条；已轮换 R 条；门禁已/未落地>`
- 定时任务：`<共 N 个条目，永不触发 X 个，DST 风险 Y 个，漂移 Z 项>`
- 最高优先级动作：`<一句话>`
- 验收状态：`<通过 / 有条件通过 / 未通过>`

## 1. 密钥扫描结果

| # | 规则 | 严重级 | 位置（文件:行） | 首次引入提交 | 状态 | 建议 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `<rule-id>` | `<high>` | `<path:line>` | `<short-sha>` | `<已轮换 / 待轮换>` | `<动作>` |

证据：

```console
$ leakpulse scan . --history 50 --fail-on high
<脱敏输出，保留前 4 / 后 4 位>
$ echo $?
<0|1|2>
```

基线：

```console
$ leakpulse scan . --write-baseline .leakpulse-baseline.json
<命中数，退出码 0>
$ leakpulse scan . --baseline .leakpulse-baseline.json --fail-on high
<新增命中数，退出码 0|1>
```

门禁验证（用运行时生成的假值，不写真实密钥）：

```console
$ echo 'TOKEN=<runtime-fake-value>' > demo.tmp && git add demo.tmp && git commit -m demo
<被 pre-commit 拦截的输出，脱敏>
$ echo $?
1
```

## 2. 定时任务结果

### 2.1 条目清单

| # | 来源 | 计划 | 命令 / Unit | 下次触发 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `<user crontab>` | `<30 2 * * *>` | `<db-snapshot.sh>` | `<2026-03-09 02:30 +08:00>` | `<DST 风险>` |

### 2.2 漂移对账

```console
$ cronpulse drift <crontab> --expect <manifest.json>
actual: <N> entries; expected: <M>; matched: <K>
missing (<a>): ...
unexpected (<b>): ...
changed (<c>): ...
$ echo $?
4
```

```console
$ cronpulse timer-drift <paths> --expect <timers.json>
<同上，另含 duplicates / never_fires 告警>
$ echo $?
4
```

修复后复跑：

```console
$ cronpulse drift <crontab> --expect <manifest.json>; echo $?
0
```

## 3. 发现与建议（按优先级）

| 优先级 | 发现 | 影响 | 建议动作 | 责任方 | 目标日期 |
| --- | --- | --- | --- | --- | --- |
| P0 | `<仍有效的密钥已进入公开历史>` | `<可直接被滥用>` | `<立即轮换 + 复查审计日志>` | `<客户>` | `<日期>` |
| P1 | `<备份任务落在 DST gap>` | `<每年一次漏跑>` | `<改为 03:30 或使用 timer>` | `<客户>` | `<日期>` |
| P2 | `<timer 清单无 Unit= 字段>` | `<产生假 changed>` | `<补全清单>` | `<双方>` | `<日期>` |

## 4. 未覆盖范围与假设

- `<未扫描的仓库 / 未检查的主机>`
- `<假设：生产凭据已由客户轮换；我们未验证轮换是否生效>`
- `<未做渗透测试、未做合规认证>`

## 5. 后续 30 天建议

- [ ] `<第 1 周：轮换剩余 P0 凭据并刷新基线>`
- [ ] `<第 2 周：把 drift 对账接进每周巡检>`
- [ ] `<第 4 周：复查新增告警是否真的会响>`

## 6. 签收

| 项 | 客户 | 交付方 |
| --- | --- | --- |
| 验收结论 | `<通过 / 有条件通过>` | `<通过 / 有条件通过>` |
| 签字 / 日期 | `<姓名 YYYY-MM-DD>` | `StackPulse Lab YYYY-MM-DD` |
| 备注 | `<...>` | `<...>` |
