# 定时任务没跑：一次 DST 缺 02:30 与 systemd timer 清单漂移的排查实录

> 场景：一个纽约节点上的每日备份，春季少跑一次、秋季多跑一次；迁到 systemd 后，
> 又有一批 timer 被手工改过而没人发现。文中命令与退出码均在本机实际运行，
> 示例 unit 与清单为复现用文件，不含任何真实主机信息。

## 1. 事故：备份「消失」了一天，又「重复」了一天

监控在三月第二个周一报：**周日 02:30 的全量备份缺失**。日志里没有任何
`failed`，服务是成功的——因为任务根本没被启动。

同一套配置到了十一月第一个周日，又变成**同一次备份跑了两遍**，下游对账脚本
不幂等，重复生成了一份账单。

两次都不是 cron 写错了，而是 DST：

- 2026-03-08 美国东部进入夏令时，本地时间 `02:00 → 03:00`，**02:30 不存在**；
- 2026-11-01 回拨，`01:00` 到 `02:00` 之间出现两次，**01:00/01:30 各发生两次**。

经典 cron 按挂钟时间匹配，守护进程遇到不存在的时刻通常直接跳过且不报错。于是
「任务没跑」这件事，只能等下游戏务发现缺数据。

## 2. 第一层排查：把「不存在的时间」显式打印出来

```console
$ cronpulse next "30 2 * * *" --tz America/New_York --after 2026-03-07T12:00 -n 2
30 2 * * *  (after 2026-03-07T12:00:00-05:00)
 1. 2026-03-09 02:30:00-04:00
 2. 2026-03-10 02:30:00-04:00
note: skipped 1 wall-clock time(s) that do not exist (DST gap): 2026-03-08 02:30:00
$ echo $?
0
```

**退出码是 0**，因为表达式合法、任务也确实会在别的日子触发。这类问题不能靠
「命令失败」发现，只能靠预览里的 `note:`。换成 `--json` 时，同样的信息在
`dst.skipped` 里，可以直接进巡检报表。

秋季重叠则相反——同一个挂钟时间对应两个真实时刻：

```console
$ cronpulse next "*/30 1 * * *" --tz America/New_York --after 2026-10-31T23:30 -n 4
*/30 1 * * *  (after 2026-10-31T23:30:00-04:00)
 1. 2026-11-01 01:00:00-04:00
 2. 2026-11-01 01:30:00-04:00
 3. 2026-11-01 01:00:00-05:00
 4. 2026-11-01 01:30:00-05:00
note: 2 wall-clock time(s) occur twice (DST overlap), both listed: 2026-11-01 01:00:00, 2026-11-01 01:30:00
```

偏移量 `-04:00` / `-05:00` 是判断「这是两次真实执行」的关键证据。做幂等要对
UTC 时间戳去重，而不是对本地 `01:00` 去重。

`cronpulse explain` 还会提示时区来源，避免「我以为 cron 认 `CRON_TZ`」的误解：

```console
$ cronpulse explain "30 2 * * *"
expression : 30 2 * * *
fields     : minute=30; hour=2; day-of-month=*; month=*; day-of-week=*
hint       : cron daemons run in the system timezone; classic Vixie cron also honours a per-crontab CRON_TZ=<IANA zone> line, systemd timers ignore CRON_TZ (use OnCalendar with its own DST rules). Preview another zone with --tz.
```

要点：**systemd timer 完全不认 `CRON_TZ`**。主机时区、`CRON_TZ`、`OnCalendar=`
三套时间语义混用时，最容易出现「预览是一回事、线上是另一回事」。

## 3. 第二层排查：timer 清单漂移

备份任务后来从 cron 迁到了 systemd timer。迁移脚本、手工救火、代码合并之后，
`/etc/systemd/system/*.timer` 和「我们以为的定时任务清单」已经不一致了。

构造一台复现主机（`units/` 下 5 个 timer）：

- `backup.timer`：清单要求 `daily`，实际被改成 `Mon 09:00`；
- `report.timer`：只剩 `Mon..Fri 09:00`，清单里的 `Fri 18:00` 不见了；
- `audit.timer`：`OnBootSec=15min` + `OnUnitActiveSec=1d`，**相对触发器**；
- `legacy-sweep.timer`：`OnCalendar=*-02-30 00:00`，2 月没有 30 号；
- `dup.timer`：一次 merge 留下了两行相同的 `OnCalendar=hourly`。

清单 `timers.json` 声明「应该存在什么」：

```json
{
  "timers": [
    {"name": "backup.timer", "calendar": "daily", "service": "backup.service"},
    {"name": "report.timer", "calendars": ["Mon..Fri 09:00", "Fri 18:00"]},
    {"name": "legacy-sweep.timer", "calendar": "*-02-30 00:00", "service": "legacy-sweep.service"}
  ]
}
```

第一次直接对账，工具先拒绝猜测相对定时器：

```console
$ cronpulse timer-drift units --expect timers.json
cronpulse: units/audit.timer:5: OnBootSec= is a relative timer with no fixed calendar; pass --allow-relative to skip it
$ echo $?
2
```

这是刻意设计：`OnBootSec` 没有固定日历，静默忽略会给出「清单全绿」的错误结论。
确认这类 timer 另行监控后，显式放行：

```console
$ cronpulse timer-drift units --expect timers.json --allow-relative
actual: 5 timer calendars; expected: 4; matched: 1
missing (1):
  report.timer  Fri 18:00
unexpected (2):
  dup.timer  hourly  service=dup.service
  dup.timer  hourly  service=dup.service
changed (2):
  backup.timer: daily -> Mon 09:00
  report.timer: calendar unchanged (service - -> report.service)
warning: duplicate OnCalendar= entries (1):
  dup.timer  hourly  service=dup.service
warning: timers that never fire (1):
  legacy-sweep.timer  *-02-30 00:00  service=legacy-sweep.service
$ echo $?
4
```

四条线索一次给全：

1. **missing**：清单里有、磁盘上没有 → `report.timer` 的周五 18:00 报表确实没跑；
2. **changed**：`backup.timer` 被改成 `Mon 09:00`，于是「每日备份」变成「每周一备份」；
3. **unexpected**：`dup.timer` 出现两条，因为 unit 里重复写了 `OnCalendar=`；
4. **warning**：`*-02-30` 在 8 年窗口内永远不会触发。

### 一个容易误判的细节：`Unit=` 属于身份

注意 `report.timer: calendar unchanged (service - -> report.service)`。日历明明一样，
为什么报 `changed`？因为清单里没写 `service`，而 unit 里写了
`Unit=report.service`。**identity = 名字 + 服务目标 + 日历**，换服务不是「同一个
任务改了时间」，而是指向了另一个服务。

教训：清单里把 `service` 写全，否则第一次接入就会收到一条「日历没变却 changed」
的噪声，团队会以为工具误报。

## 4. 修复后复验：从 exit 4 到 exit 0

修 unit（恢复 `daily`、补回 `Fri 18:00`、删掉重复行与永不触发的 timer），
并把 `service` 补进清单：

```console
$ cronpulse timer-drift fixed2 --expect timers.fixed.json --allow-relative
actual: 3 timer calendars; expected: 3; matched: 3
no drift: timer units match the expected manifest
$ echo $?
0
```

再跑一次**不带** `--allow-relative` 的命令，仍然以 `2` 拒绝：

```console
$ cronpulse timer-drift fixed2 --expect timers.fixed.json
cronpulse: fixed2/audit.timer:5: OnBootSec= is a relative timer with no fixed calendar; pass --allow-relative to skip it
$ echo $?
2
```

这不是回归，而是提醒：相对 timer 只能被「显式」跳过。CI 里保留这个失败版本，
可以防止有人把 `--allow-relative` 当成默认参数顺手加进脚本。

## 5. 接入巡检与 CI：先区分退出码，再决定告警级别

| 退出码 | 含义 | 建议动作 |
| --- | --- | --- |
| `0` | 清单一致 / 预览成功 | 记录 |
| `2` | 表达式非法、文件不可读、相对 timer 未放行 | 配置错误，立即修 |
| `3` | 8 年窗口内不会触发 | 计划无效，立即修 |
| `4` | 存在漂移或告警 | 比对清单，按 missing/changed 分级 |

每日巡检里用 JSON 做一次压缩，先看总量再看细节：

```console
$ cronpulse timer-drift units --expect timers.json --allow-relative --json \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print("drift={} missing={} unexpected={} changed={} duplicates={} never_fires={}".format(d["drift"], len(d["missing"]), len(d["unexpected"]), len(d["changed"]), len(d["duplicates"]), len(d["never_fires"])))'
drift=True missing=1 unexpected=2 changed=2 duplicates=1 never_fires=1
$ echo ${PIPESTATUS[0]}
4
```

注意 `${PIPESTATUS[0]}`：管道让 `python3` 的退出码变成 0，真正要判断的是
`cronpulse` 的 `4`。CI 里写成 `set -o pipefail`，或者把 JSON 先落盘再解析。

DST 侧同理，`cronpulse next` 的 `note:`/`dst.skipped` 不会让命令失败（退出码仍
是 0），所以巡检脚本要显式检查这两个字段，而不是只看退出码：

```console
cronpulse next "30 2 * * *" --tz America/New_York --after "$(date -Iseconds)" -n 3 --json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("upcoming:", len(d["runs"]), "skipped:", len(d.get("dst",{}).get("skipped",[])), "ambiguous:", len(d.get("dst",{}).get("ambiguous",[])))'
```

## 6. 复盘清单

1. **别把关键任务放在 02:00–03:00 的本地挂钟时间**——几乎所有 DST 时区都在这个
   区间跳过或重复。要跨时区稳定，就用 UTC 或在 04:00 之后执行。
2. **「命令成功」不等于「任务跑过」**：DST 缺口的任务不会产生 failed 日志。
   用 `--tz` 预览未来 3 次，并检查 `note:` / `dst.skipped`。
3. **幂等按 UTC 时间戳做**：秋季重叠时本地 `01:00` 会出现两次，只按本地时间
   去重必然漏掉第二次。
4. **timer 清单要进 Git**：`timers.json` 和 unit 文件一起评审，迁移脚本改了什么
   在 diff 里能看见。
5. **`Unit=` 写全**：它是 timer 身份的一部分，缺省会在对账时产生 changed 噪声。
6. **相对触发器显式处理**：`OnBootSec=` / `OnUnitActiveSec=` 没有固定日历，
   要么 `--allow-relative` 并在别处监控，要么换成固定 `OnCalendar=`。
7. **drop-in 不合并**：依赖 `*.timer.d/` 覆盖时，`timer-drift` 要直接指向具体
   unit 文件，否则比对的是「基础文件」而不是「实际生效配置」。
8. **CI 保留严格模式**：`--allow-relative` 只给已知的相对 timer；其余路径不带，
   让退出码 2 继续拦人。

## 7. 本轮真实退出码汇总

| 命令 | 退出码 |
| --- | --- |
| `next "30 2 * * *" --tz America/New_York`（DST gap） | `0` + `note: skipped 1` |
| `next "*/30 1 * * *" --tz America/New_York`（DST overlap） | `0` + 4 个真实时刻 |
| `explain "30 2 * * *"` | `0` + `CRON_TZ` 提示 |
| `timer-drift units`（有相对 timer） | `2` |
| `timer-drift units --allow-relative`（漂移） | `4` |
| `timer-drift fixed2 --allow-relative`（修复后） | `0` |
| `timer-drift fixed2`（严格模式） | `2` |
| `calendar "*-02-30 00:00"` | `3` |
| `check "0 0 30 2 *"` | `3` |

工具：`pip install cronpulse-cli`（命令名 `cronpulse`，零第三方依赖，不联网、
不落盘）。本文所有 unit、清单与命令都可以在本地复现。
