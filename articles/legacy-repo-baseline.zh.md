# 存量仓库接入密钥扫描：用基线模式 10 分钟落地，且不放过新泄露

> 面向已有一堆历史提交、又想把「防手滑」门禁真正接进 CI 的团队。
> 文中命令与退出码均在本地实际运行，示例密钥为运行时生成的假值，输出已脱敏。

## 为什么大多数密钥扫描器在存量仓库里活不过一周

新仓库接扫描器很顺：第一次跑就是绿的。存量仓库不一样。

你兴冲冲加上 `gitleaks` / `trufflehog` / `leakpulse`，第一次 CI 的结果是：

- 三年前测试夹具里的假 AWS Key；
- 已经轮换过、但旧值还留在历史里的 GitHub Token；
- 示例配置里的 `sk-...` 占位符；
- 已经下线的服务 Webhook。

几十条 `HIGH` 一起亮红，没人能在当天全部处理完。为了不被红灯挡住发版，团队只有两个选择：加 `ignore` 把规则关掉，或者把这一步从 CI 里删掉。两种做法的结果一样——**从此以后真正的新泄露也不会被发现**。

问题不在规则数量，而在**接入路径**：存量问题需要一个可被评审、可被逐步消化的「已知集合」，而 CI 只应该对**新增**问题失败。

这就是 LeakPulse v0.5.0 的基线模式要解决的事。

## 基线里到底存了什么

`leakpulse scan --write-baseline FILE` 会把当前所有命中写成一份指纹快照：

```json
{
  "schema": "leakpulse-baseline/1",
  "tool": "leakpulse 0.5.0",
  "created_at": "2026-11-27T13:00:36Z",
  "count": 1,
  "fingerprints": [
    "56d8005470bdec2761ef"
  ]
}
```

每条指纹是 `规则 id + 文件路径 + 匹配到的值` 的 SHA-256 前 20 位。因此：

- **文件里没有密钥，也没有脱敏片段**，可以安全提交、贴进 PR、给安全同学评审；
- **指纹不含行号**：上下移动代码不会让旧命中重新报警；
- **路径参与指纹**：把带密钥的文件改名、搬到别的目录，会被当成新问题（这正是绕过评审的常见手法）；
- **值参与指纹**：密钥轮换后旧指纹失效、新指纹出现，CI 会再次报错——这是期望行为，不是误报。

一句话：基线是「已评审的存量清单」，不是「静音键」。

## 10 分钟落地步骤（真实终端记录）

准备：Python 3.9+、git。演示仓库里有一个 2019 年迁移遗留的 `legacy.py`，第二行硬编码了一个假 DeepSeek Key（运行时随机生成）。

### 第 1 步：先看清存量（命令会失败，这是正常的）

```console
$ leakpulse scan . --history 20
HIGH   deepseek-key  legacy.py:2  sk-C****************VNPk  DeepSeek API key (sk-…, same shape as OpenAI keys)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 2 files and 1 commit in 0.01s.
$ echo $?
1
```

`--history 20` 表示同时扫描最近 20 个提交，所以「已经提交过一次」的密钥也跑不掉。

### 第 2 步：生成基线（该命令固定退出 0）

```console
$ leakpulse scan . --history 20 --write-baseline leakpulse-baseline.json
leakpulse: recorded 1 fingerprint(s) in leakpulse-baseline.json
HIGH   deepseek-key  legacy.py:2  sk-C****************VNPk  DeepSeek API key (sk-…, same shape as OpenAI keys)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 2 files and 1 commit in 0.01s.
$ echo $?
0
```

注意两点：

1. 它**仍然打印完整报告**，方便你在提交快照前逐条判断「哪些是真遗留、哪些其实该马上轮换」；
2. 固定退出 `0`，因为「生成快照」本身不是对仓库的判定。判定发生在下一步。

评审并提交快照：

```bash
git add leakpulse-baseline.json
git commit -m "chore: record known leakpulse findings"
```

### 第 3 步：只对新增问题报错

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
No potential secrets found. Scanned 3 files and 1 commit in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
0
```

现在 CI 是绿的，而且**没有关掉任何规则**。

### 第 4 步：验证它真的会拦住新泄露

加一个新文件，写入假 GitHub Token（同样运行时生成）：

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
HIGH   github-token  fresh.py:1  ghp_****************71fT  GitHub token (classic app/OAuth/refresh)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 4 files and 2 commits in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
1
```

JSON 输出里能直接看出「新问题 1 条、被基线抑制 1 条」，适合丢给脚本做 triage：

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json --format json \
    | python3 -c "import json,sys;d=json.load(sys.stdin);print('findings:',[f['path'] for f in d['findings']],'baseline:',d['baseline'])"
findings: ['fresh.py'] baseline: {'file': 'leakpulse-baseline.json', 'suppressed': 1}
```

### 第 5 步：确认基线的边界（两个容易误解的点）

**移动行号不会重新报警**。在 `legacy.py` 顶部插入两个空行，密钥从第 2 行挪到第 4 行：

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
... 1 known finding suppressed by baseline.
$ echo $?
1        # 唯一的失败来自第 4 步新增的 fresh.py，不是旧的 legacy.py
```

**轮换密钥会重新报警**。把 `legacy.py` 里的旧值换成新值：

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
HIGH   github-token  fresh.py:1    ghp_****************71fT  ...
HIGH   deepseek-key  legacy.py:4  sk-q****************XRrv  ...

2 potential secrets found (2 high, 0 medium, 0 low) Scanned 4 files and 2 commits in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
1
```

旧指纹匹配的是旧值，所以新值必然是新问题。这正好覆盖了「轮换后忘了更新配置、又把新 Key 提交回去」的事故。

## CI 接入

### GitHub Actions（推荐，零配置）

```yaml
name: secret-scan
on: [push, pull_request]
permissions:
  contents: read
jobs:
  leakpulse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 200        # 历史扫描需要提交
      - uses: stackpulse-lab/leakpulse@v0.5.0
        with:
          history: "200"
          baseline: leakpulse-baseline.json
          fail-on: high
```

`fetch-depth` 必须大于 1，否则 `--history` 只能看到最后一个提交。Action 会以所引用 tag 的代码安装，不依赖 PyPI，也不需要 `setup-python`。

### 其它 CI / 本地

```bash
pip install leakpulse==0.5.0
leakpulse scan . --history 200 --baseline leakpulse-baseline.json --fail-on high
```

配合 SARIF，还能把新增问题直接推到 GitHub Code Scanning 的 Security 面板：

```bash
leakpulse scan . --history 200 --baseline leakpulse-baseline.json \
  --format sarif --output leakpulse.sarif
```

### 和 pre-commit 的关系

基线管「历史 + CI」，钩子管「提交前」。两者可以同时用：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/stackpulse-lab/leakpulse
    rev: v0.5.0
    hooks:
      - id: leakpulse          # 只扫暂存区，不需要基线
```

暂存区检查天然是「增量」的，不需要基线文件；基线只用于全树 + 历史的 CI 任务。

## 运维约定：让基线不腐烂

基线是资产，也有保质期。建议把下面几条写进团队约定：

1. **谁生成、谁评审**：快照必须由提交人以外的人看一眼，尤其是 `HIGH` 条目；不要用 `--write-baseline` 直接把红灯刷绿。
2. **同时排轮换**：进入基线不等于安全。给每条遗留命中建一个轮换工单，轮换完成后指纹自然失效，报错一次后删掉旧条目即可。
3. **基线随分支走**：不同 release 分支的遗留集合不同，基线文件跟代码一起提交，不要放在 CI 的缓存里。
4. **定期收缩**：每季度用 `--write-baseline` 重新生成一次并对比 `count`。数字应该单调下降；上升说明有人在往基线里塞新问题。
5. **历史深度固定**：生成与使用基线时用同一个 `--history N`。突然把 N 从 50 调到 200，会一次冒出更多历史命中——这是新发现，不是回归。
6. **路径变更视为新增**：重命名文件后基线失效是设计使然。确认是同一份遗留后再更新快照。

## 踩坑记录（都是本轮实测踩到的）

- **临时文件也算工作区**：第一次演示时，我把生成假密钥的 `.demo-secrets.json` 放在了演示仓库目录里，结果它被当成两个独立 `HIGH` 命中（`github-token` + `openai-key`）一起扫出来。演示数据要放在仓库外，否则你会在基线里记录一堆本不该存在的条目。
- **同一段文本可能命中多条规则**：`sk-` 开头的 Key 同时符合 `openai-key` 与 `deepseek-key`，LeakPulse 通过规则顺序只报最具体的一条（`deepseek-key`）。自己写规则时要注意优先级，否则一条泄露会变成多条噪音。
- **`--write-baseline` 永远退出 0**：不要把它当成「扫描通过」。流水线里只应该用 `--baseline` 做门禁。
- **两个参数互斥**：同时给 `--write-baseline` 和 `--baseline` 会以退出码 `2` 拒绝执行，避免「一边读一边写」的歧义。

## 10 分钟检查表

```text
[ ] leakpulse scan . --history 200                     # 先看存量，接受 exit 1
[ ] leakpulse scan . --history 200 --write-baseline …  # 生成快照，评审 diff
[ ] git add leakpulse-baseline.json && git commit
[ ] leakpulse scan . --history 200 --baseline …        # 确认 exit 0
[ ] 新增一个假密钥验证 exit 1（别提交它）
[ ] CI 里加 Action + fetch-depth: 200
[ ] 给每条 HIGH 建轮换工单，而不是只加基线
```

## 小结

存量仓库接密钥扫描，失败点通常不是「扫不出来」，而是「一次扫出太多，团队只能关掉」。基线模式把接入拆成两步：**先把已知问题变成可评审的指纹清单，再让 CI 只对新增问题失败**。它不隐藏任何东西——轮换、改名、新文件都会重新报警——只是把「历史债务」和「今天的新错误」分开处理。

工具是 MIT、零依赖、本地运行：<https://github.com/stackpulse-lab/leakpulse>

```bash
pip install leakpulse==0.5.0
```
