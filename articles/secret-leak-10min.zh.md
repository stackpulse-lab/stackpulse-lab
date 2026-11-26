# 密钥泄露后的 10 分钟：一份可复现的应急与防复发手册

> 作者：StackPulse Lab（栈脉工坊） · 2026-11-27 · 工具：[LeakPulse v0.4.0](https://github.com/stackpulse-lab/leakpulse)
>
> 本文所有输出均来自一台普通 Linux 机器上的真实运行；示例密钥为运行时生成的假值，仓库里不保存任何可用凭据。

---

## 先说结论

密钥泄露后，**轮换永远排在清理前面**。

`git rm`、改 `.env`、删分支都不会让已经出现在历史、日志、fork、CI 缓存和截图里的密钥失效。
真正让攻击者手里那把钥匙作废的，只有**在服务端吊销/轮换**。

下面是一条 10 分钟时间线：先止损，再取证，最后才谈清理和防复发。文中每条命令都可直接复制复现。

| 时间 | 动作 | 目标 |
| --- | --- | --- |
| T+0 | 停用/轮换凭据 | 让泄露的值立即失效 |
| T+2 | 本地历史取证 | 确认泄露范围与引入提交 |
| T+5 | 评估影响面 | 判断是否需要通知、审计日志、加白名单 |
| T+7 | 清理历史（可选） | 降低二次扩散面，但**不能替代轮换** |
| T+9 | 加门禁 | 让下一次提交在本地就被拦下 |
| T+10 | 复盘归档 | 把事故变成可复用的检查项 |

---

## T+0：先让密钥失效，再讨论别的

不同凭据的处置入口不同，但动作只有两类：**吊销**或**轮换**。

| 凭据类型 | 处置位置（示例） | 注意 |
| --- | --- | --- |
| DeepSeek API Key | 平台「API Keys」页 | 先建新 Key 再删旧 Key，避免业务中断 |
| 阿里云 AccessKey | RAM 控制台 → 用户 → AccessKey | 优先改用 RAM 角色/STS 临时凭据 |
| 腾讯云 SecretId/SecretKey | 访问管理 CAM → API 密钥管理 | 检查是否绑定了子账号与权限策略 |
| 飞书/企微/钉钉机器人 Webhook | 群机器人设置 → 重置/重新生成 | 旧 URL 立即失效，重新分发新地址 |
| 爱发电 API Token | 开发者后台 | 同时检查订单回调地址是否被篡改 |

同时做三件事：

1. **记录时间线**：谁在什么时候发现、什么时候吊销、什么时候换新。事故复盘和合规审计都需要。
2. **查调用日志**：轮换前先导出最近的调用记录，确认有没有异常来源或异常用量。删得太快会把证据一起删掉。
3. **最小权限复核**：这把 Key 为什么能读到生产数据？顺手把权限收窄，比只换一个字符串更有价值。

> 常见误区：只改 `.env` 就以为结束了。`.env` 只是本地副本，泄露的是**服务端那把钥匙**。

---

## T+2：取证——先看历史，不要先看工作区

大多数「我已经删掉了」的仓库，工作区确实是干净的，但历史里还躺着原文。
下面用一个两提交的演示仓库复现这个场景。

### 复现实验：造一个「已经修好」的仓库

```bash
mkdir -p /tmp/leak-case && cd /tmp/leak-case
git init -q -b main
git config user.email demo@example.invalid
git config user.name demo

# 运行时生成假凭据：文章本身不包含任何完整密钥字面量
python3 - <<'PY'
from pathlib import Path

tail = "0123456789abcdefghij" * 2          # 40 个字符
Path("config.py").write_text(
    'DEEPSEEK_API_KEY = "sk-demo' + tail[:28] + '"\n'
    'ALIYUN_ACCESS_KEY_ID = "LTAI' + tail[:16] + '"\n'
)
hexish = "1" * 8 + "-" + "2" * 4 + "-" + "3" * 4 + "-" + "4" * 4 + "-" + "5" * 12
Path("notify.sh").write_text(
    'curl -s "https://open.feishu.cn/open-apis/bot/v2/hook/' + hexish + '"\n'
)
PY

git add -A && git commit -qm "feat: wire up deploy notifications"
```

第一个提交把凭据硬编码进了两个文件。接着模拟「发现后修掉」：

```bash
git rm -q config.py notify.sh
cat > config.py <<'EOF'
import os
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
ALIYUN_ACCESS_KEY_ID = os.environ["ALIYUN_ACCESS_KEY_ID"]
EOF
cat > notify.sh <<'EOF'
curl -s "$FEISHU_WEBHOOK" -H 'Content-Type: application/json' -d '{"msg_type":"text"}'
EOF
git add -A && git commit -qm "fix: stop hardcoding credentials"
```

现在仓库看起来「已经安全了」。先按直觉扫工作区：

```console
$ leakpulse scan . --history 0
No potential secrets found. Scanned 2 files in 0.00s.
$ echo $?
0
```

干净，退出码 0。但这正是最容易误判的地方——历史还没看。

### 扫历史：3 条命中，全部指向同一个旧提交

```console
$ leakpulse scan . --history 20
HIGH   deepseek-key         config.py:1 @1d788669  sk-d****************4567  DeepSeek API key (sk-…, same shape as OpenAI keys)
HIGH   aliyun-access-key-id config.py:2 @1d788669  LTAI************cdef    Alibaba Cloud (Aliyun) AccessKey ID
HIGH   feishu-webhook       notify.sh:1 @1d788669  1111****************5555 Feishu/Lark bot webhook token

3 potential secrets found (3 high, 0 medium, 0 low) Scanned 2 files and 2 commits in 0.01s.
$ echo $?
1
```

三个关键信息：

- **提交号** `@1d788669`：定位到引入提交，便于通知作者、评估影响范围；
- **文件与行号**：直接定位原始上下文；
- **脱敏值**：输出只保留首尾各 4 位，可以安全贴进工单或群聊，不会造成二次泄露。

退出码 `1` 表示命中达到 `--fail-on high`（默认），可以直接接 CI 门禁。

> 注意 `--history N` 走的是当前分支最近 N 个提交（`git rev-list --max-count=N HEAD`）。
> 多分支仓库要额外补扫，见 T+7 的「全分支补齐」。

### 一条命令生成三种交付物

事故处理往往需要同时给三类人看结果：工程师看终端，CI 看 SARIF，评审/合规看 HTML。

```bash
# 机器可读：接工单系统或写 triage 脚本
leakpulse scan . --history 500 --format json --output leak.json

# SARIF 2.1.0：上传 GitHub Code Scanning
leakpulse scan . --history 500 --format sarif --output leak.sarif

# 单文件 HTML：无 JS、无远程资源、命中值已脱敏，适合做附件
leakpulse scan . --history 500 --format html --output leak.html
```

三种格式共享同一份扫描结果与退出码，不会出现「终端说 3 条、报告说 0 条」的分裂。

JSON 结果可以三行内变成工单列表（只用标准库）：

```bash
python3 - <<'PY'
import json
for f in json.load(open("leak.json"))["findings"]:
    print(f'{f["severity"]}\t{f["rule"]}\t{f["path"]}:{f.get("line")}\t{f.get("commit", "-")}')
PY
```

```console
high    deepseek-key          config.py:1   1d788669
high    aliyun-access-key-id  config.py:2   1d788669
high    feishu-webhook        notify.sh:1   1d788669
```

---

## T+5：评估影响面，而不只是「有几个文件」

命中数不等于风险。按下面顺序过一遍：

1. **这些凭据还有效吗？** 如果已经在 T+0 轮换，剩余风险主要是「历史可读」而非「可直接利用」。
2. **仓库是公开还是私有？** 公开仓库要按「已泄露」处理；私有仓库仍需检查 fork、协作者与 CI 日志。
3. **凭据的权限边界**：只读还是可写？能否访问生产数据库、对象存储、消息队列？
4. **是否出现在别处**：CI 变量、Docker 镜像层、构建产物、Issue 截图、本地 `.env` 备份。LeakPulse 只扫仓库，不扫这些地方。
5. **是否需要外部动作**：客户数据受影响时的通知义务、云厂商工单、审计留档。

把结论写成一句话，例如：
「1 个 DeepSeek Key（只读、限额）+ 1 个阿里云 AK（可写 OSS）+ 1 个飞书 Webhook；已轮换；公开仓库历史仍含旧值；无异常调用。」

---

## T+7：清理历史是「可选项」，而且有代价

历史清理能降低二次扩散面，但它**不是安全边界**：任何已经 clone 过的副本、fork、CI 缓存都不会自动消失。

如果团队确认要清理，基本流程是：

```bash
# 需要单独安装 git-filter-repo；不要在没有备份的仓库上直接操作
git filter-repo --path config.py --path notify.sh --invert-paths

# 重新添加远端并强推所有分支/标签（团队必须同步：所有人重新 clone）
git remote add origin <repo-url>
git push --force --all
git push --force --tags
```

执行前必须确认：

- 所有协作者已知情，且愿意重新 clone（否则旧历史会被再次推回来）；
- 已保存事故证据（提交号、日志、时间线）；
- 托管平台侧的缓存/fork/PR 引用是否需要额外处理；
- **旧凭据已经轮换**——这一步不做，清理历史只是心理安慰。

对多数小团队，更划算的顺序是：**轮换 → 加门禁 → 把历史清理排进计划**，而不是反过来。

### 全分支补齐（`--history` 只跟当前分支）

```bash
for ref in $(git for-each-ref --format='%(refname:short)' refs/heads refs/tags); do
  git checkout -q --detach "$ref"
  echo "== $ref =="
  leakpulse scan . --history 500 --quiet || echo "!! findings at $ref"
done
git checkout -q main
```

先在干净工作区执行；有未提交改动时先 `git stash`。

---

## T+9：防复发——把检查放在提交之前

事故之后最常见的第二次事故，是「加了一条规则，但没人执行」。门禁要满足两个条件：**默认开启**、**失败即阻断**。

### 方案一：pre-commit（本地，最快反馈）

`.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/stackpulse-lab/leakpulse
    rev: v0.4.0
    hooks:
      - id: leakpulse          # 只扫暂存区，提交前拦截
      - id: leakpulse-worktree # 整树扫描，不含历史
```

```bash
pipx install pre-commit
pre-commit install
pre-commit run --all-files
```

不想引入 pre-commit 也可以用它自带的钩子：

```bash
leakpulse install-hook
```

实测拦截效果（暂存一个假 GitHub Token 后提交）：

```console
$ git commit -m "oops"
HIGH   github-token  bad.py:1  ghp_****************1234  GitHub token (classic app/OAuth/refresh)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 1 file in 0.01s.
$ echo $?
1
```

提交被拒绝，文件仍在暂存区，修掉再提交即可。

> 钩子是 **fail-closed** 的：如果 `leakpulse` 不在 PATH 里，钩子会直接失败而不是放行。
> 用虚拟环境时，先激活环境再提交；或在钩子里设置 `LEAKPULSE_SRC`。

### 方案二：CI 门禁 + Code Scanning（团队，不可绕过）

```yaml
name: secret-scan
on: [push, pull_request]

permissions:
  contents: read
  security-events: write

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: stackpulse-lab/leakpulse@v0.4.0
        with:
          path: "."
          history: "100"
          fail-on: high
          format: sarif
          output: leakpulse.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: leakpulse.sarif
```

- `history: "100"` 让 CI 也能发现「曾经提交过」的密钥；
- `continue-on-error: true` + `if: always()` 保证即使门禁失败，SARIF 仍会出现在 Security 面板；
- 想先观察再阻断，把 `fail-on` 调成 `never`，跑一周再收紧。

### 三条低成本规范

1. **测试夹具显式放行**：假密钥后面加 `# leakpulse:allow`，而不是把整个 `tests/` 排除掉。
2. **示例配置只放占位符**：`.env.example` 用 `your-key-here`，不要复制真实值再改一半。
3. **定期轮换**：把「季度轮换」写进日历；泄露是被动的，轮换是主动的。

---

## T+10：复盘清单（可直接抄进事故模板）

- [ ] 凭据已在服务端吊销/轮换，新凭据已生效
- [ ] 调用日志已导出并检查异常来源/用量
- [ ] 泄露范围已确认：文件、提交、分支、是否公开
- [ ] 影响面已评估：权限、数据、客户、合规义务
- [ ] 证据已归档：提交号、扫描报告（JSON/SARIF/HTML）、时间线
- [ ] 本地钩子或 CI 门禁已开启，并验证过一次真实拦截
- [ ] 历史清理计划已排期（或明确决定不清理，并记录理由）
- [ ] 复盘结论写入团队文档，下一次演练有据可依

---

## 附：10 分钟命令卡片

```bash
# 1) 取证：工作区 + 最近 500 个提交
leakpulse scan . --history 500

# 2) 三种交付物
leakpulse scan . --history 500 --format json  --output leak.json
leakpulse scan . --history 500 --format sarif --output leak.sarif
leakpulse scan . --history 500 --format html  --output leak.html

# 3) 本地门禁
leakpulse install-hook

# 4) 自检：确认工具本身没有误报/漏报
leakpulse scan . --history 0 --fail-on high
```

LeakPulse 是 MIT 许可、零第三方依赖的本地扫描器：不联网、不上传、无遥测。
它不能判断密钥是否仍然有效，也不替代 SAST——**发现即轮换**，这是它能给出的最重要建议。

---

*工具仓库：<https://github.com/stackpulse-lab/leakpulse> · 问题与建议：欢迎开 Issue。*
