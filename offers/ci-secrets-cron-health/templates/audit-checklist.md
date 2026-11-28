# 体检清单 / Audit checklist

> 逐项打勾并记录证据（命令、退出码、脱敏输出）。没有证据的项一律视为「未验证」。

## 0. 前置

- [ ] 已收到 `intake.yml`，确认 `no_secrets_included: true`
- [ ] 确认审计授权范围（仓库列表 / 主机角色）
- [ ] 确认 Python ≥ 3.9、git 可用；工具版本已记录（`leakpulse version`、`cronpulse --version`）
- [ ] 确认在隔离副本或客户自有环境中运行，不上传任何文件

## 1. 密钥防线（LeakPulse）

### 1.1 现状取证

- [ ] 工作区扫描：`leakpulse scan . --history 0` → 记录 findings 数与退出码
- [ ] 历史扫描：`leakpulse scan . --history 50`（或全历史）→ 记录高危条目所在提交
- [ ] 输出格式核对：`--format json` 可被 `python3 -m json.tool` 解析
- [ ] 确认报告中命中值已脱敏（只保留前 4 / 后 4 位）

### 1.2 处置顺序

- [ ] 先轮换仍然有效的凭据（顺序：生产 > 预发 > 测试）
- [ ] 再评估历史重写；明确「重写不替代轮换」
- [ ] 生成基线：`--write-baseline` → 评审指纹文件（仅含 20 位哈希）
- [ ] 基线复核：`--baseline` 对存量命中退出 `0`

### 1.3 门禁落地

- [ ] pre-commit 钩子安装并在本地实测拦截（假 Token 提交被拒）
- [ ] CI 接入（Action 或 CLI），`fetch-depth` 满足历史扫描需求
- [ ] 门禁只对新增命中失败；基线文件已提交并纳入评审
- [ ] 记录轮换后刷新基线的责任人

## 2. 定时任务体检（CronPulse）

### 2.1 表达式层

- [ ] 导出当前 crontab（用户 / `/etc/crontab` / `/etc/cron.d/*`）
- [ ] 对每个条目跑 `cronpulse next ... -n 3`，确认下一次触发时间符合预期
- [ ] 对可疑条目跑 `cronpulse check`，标出永不触发（退出码 `3`）
- [ ] 时区确认：`CRON_TZ` 是否被使用；systemd timer 不认 `CRON_TZ`
- [ ] DST 检查：春季 gap 是否跳过、秋季 overlap 是否双触发

### 2.2 清单漂移

- [ ] 建立期望清单（参考 `cron-manifest.example.json` / `timers.example.json`）
- [ ] crontab 对账：`cronpulse drift <file> --expect <manifest>` → 记录 `missing / unexpected / changed`
- [ ] systemd 对账：`cronpulse timer-drift <paths> --expect <manifest>` → 记录同上 + `duplicates`
- [ ] 相对触发器（`OnBootSec` 等）已确认是否需要 `--allow-relative`
- [ ] 确认 `Unit=` 已写入清单（属于 timer 身份，缺失会产生假 `changed`）
- [ ] drop-in（`*.timer.d`）已单独列出，未假设会自动合并

### 2.3 修复验证

- [ ] 修复后复跑对账，退出码 `0`
- [ ] 记录修复前后的 diff（谁改、改了什么、何时生效）
- [ ] 为关键任务补一条「未按时完成」的外部告警（非本包范围，仅建议）

## 3. 交付物自查

- [ ] 报告中每条发现都有：命令 + 退出码 + 脱敏证据 + 建议 + 责任方
- [ ] 全文搜索确认不含真实域名凭据、Token、私钥、Webhook 完整 URL
- [ ] `leakpulse scan . --history 0` 对交付目录退出 `0`
- [ ] 报告保留期与删除方式已与客户确认
