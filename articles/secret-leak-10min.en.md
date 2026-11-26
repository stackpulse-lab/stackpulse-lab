# The first 10 minutes after a secret leak: a reproducible response playbook

> By StackPulse Lab · 2026-11-27 · Tool: [LeakPulse v0.4.0](https://github.com/stackpulse-lab/leakpulse)
>
> Every console block below comes from a real run on a plain Linux box. The demo credentials are generated at runtime; no usable secret is stored in this repository.

---

## The short version

**Rotate first. Clean up second.**

`git rm`, editing `.env`, or deleting a branch does not invalidate a key that already exists in history, logs, forks, CI caches, or screenshots. The only thing that makes the attacker's copy worthless is **revoking or rotating it on the provider side**.

What follows is a 10-minute timeline: stop the bleeding, collect evidence, and only then clean up and add a gate.

| Time | Action | Goal |
| --- | --- | --- |
| T+0 | Revoke / rotate | Make the leaked value useless |
| T+2 | Local history forensics | Establish scope and the introducing commit |
| T+5 | Blast-radius review | Decide on notifications, log review, allowlists |
| T+7 | History rewrite (optional) | Reduce spread, but never a substitute for rotation |
| T+9 | Add a gate | Block the next commit locally and in CI |
| T+10 | Write it down | Turn the incident into reusable checks |

---

## T+0: invalidate the credential before anything else

The console path differs per provider; the action is always **revoke** or **rotate**.

| Credential | Where to act (example) | Notes |
| --- | --- | --- |
| DeepSeek API key | Platform → API Keys | Create the new key before deleting the old one |
| Aliyun AccessKey | RAM console → user → AccessKey | Prefer RAM roles / STS temporary credentials |
| Tencent Cloud SecretId/Key | CAM → API key management | Check the bound sub-account and policy |
| Feishu / WeCom / DingTalk webhook | Group bot settings → reset | The old URL dies immediately; redistribute the new one |
| Afdian API token | Developer console | Also check that the callback URL was not altered |

Do three things at the same time:

1. **Keep a timeline.** Who found it, when it was revoked, when the replacement went live. You will need this for the postmortem and for any compliance review.
2. **Export recent call logs first.** Deleting the key too fast can delete the evidence of abuse with it.
3. **Re-check least privilege.** Why could that key read production data? Narrowing permissions is worth more than swapping one string.

> Common mistake: changing `.env` and calling it done. `.env` is a local copy; the leaked thing is the **key on the server**.

---

## T+2: forensics — look at history, not just the worktree

Most "I already deleted it" repositories are clean in the worktree while the plaintext still sits in history. Here is a two-commit demo that reproduces exactly that.

### Build a repo that looks "already fixed"

```bash
mkdir -p /tmp/leak-case && cd /tmp/leak-case
git init -q -b main
git config user.email demo@example.invalid
git config user.name demo

# Generate fake credentials at runtime: this article contains no complete key literal
python3 - <<'PY'
from pathlib import Path

tail = "0123456789abcdefghij" * 2          # 40 characters
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

The first commit hardcodes credentials in two files. Now simulate the "fix":

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

The repo now looks safe. Scan the worktree, as intuition suggests:

```console
$ leakpulse scan . --history 0
No potential secrets found. Scanned 2 files in 0.00s.
$ echo $?
0
```

Clean, exit code 0. That is exactly the trap: history has not been checked.

### Scan history: three findings, one old commit

```console
$ leakpulse scan . --history 20
HIGH   deepseek-key         config.py:1 @1d788669  sk-d****************4567  DeepSeek API key (sk-…, same shape as OpenAI keys)
HIGH   aliyun-access-key-id config.py:2 @1d788669  LTAI************cdef    Alibaba Cloud (Aliyun) AccessKey ID
HIGH   feishu-webhook       notify.sh:1 @1d788669  1111****************5555 Feishu/Lark bot webhook token

3 potential secrets found (3 high, 0 medium, 0 low) Scanned 2 files and 2 commits in 0.01s.
$ echo $?
1
```

Three things matter here:

- **Commit id** (`@1d788669`): the introducing commit, which tells you who to notify and what to review;
- **File and line**: the original context, without guessing;
- **Masked value**: only the first and last four characters survive, so the output is safe to paste into a ticket or chat without leaking again.

Exit code `1` means findings at or above `--fail-on high` (the default), which is exactly what a CI gate needs.

> Note: `--history N` walks the last N commits of the **current branch** (`git rev-list --max-count=N HEAD`). Multi-branch repos need the extra pass shown in T+7.

### One scan, three deliverables

Incident response usually serves three audiences: engineers read the terminal, CI consumes SARIF, reviewers and auditors want HTML.

```bash
# Machine-readable: feed a ticket system or a triage script
leakpulse scan . --history 500 --format json --output leak.json

# SARIF 2.1.0: upload to GitHub Code Scanning
leakpulse scan . --history 500 --format sarif --output leak.sarif

# Single-file HTML: no JS, no remote assets, masked values, safe as an attachment
leakpulse scan . --history 500 --format html --output leak.html
```

All three share one result set and one exit code, so the terminal and the report cannot disagree.

Turn JSON into a ticket list with nothing but the standard library:

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

## T+5: blast radius, not just a finding count

A count is not a risk assessment. Work through these in order:

1. **Is the credential still valid?** If you rotated at T+0, the remaining risk is "history is readable", not "usable right now".
2. **Is the repo public or private?** Treat a public repo as fully leaked; private repos still need fork, collaborator and CI-log review.
3. **What could the key do?** Read-only or write? Production database, object storage, message queue?
4. **Where else did it appear?** CI variables, container layers, build artifacts, issue screenshots, local `.env` backups. LeakPulse scans the repository only.
5. **Does it trigger an external obligation?** Customer-data notifications, a cloud vendor ticket, audit records.

Write the conclusion as one sentence, for example:
"One DeepSeek key (read-only, quota-limited) + one Aliyun AK (write access to OSS) + one Feishu webhook; rotated; public history still contains the old values; no anomalous calls."

---

## T+7: history rewrite is optional, and it has a price

A rewrite reduces spread, but it is **not a security boundary**: any clone, fork or CI cache that already exists will not disappear.

If the team decides to rewrite anyway:

```bash
# Requires a separate install of git-filter-repo; never run this on an unbacked-up repo
git filter-repo --path config.py --path notify.sh --invert-paths

# Re-add the remote and force-push all branches and tags (everyone must re-clone)
git remote add origin <repo-url>
git push --force --all
git push --force --tags
```

Before running it, confirm:

- every collaborator knows and will re-clone (otherwise the old history gets pushed right back);
- evidence is archived (commit ids, reports, timeline);
- platform-side caches, forks and PR refs are handled separately;
- **the old credential was already rotated** — without that, a rewrite is only psychological comfort.

For most small teams the cheaper order is: **rotate → add a gate → schedule the rewrite**, not the other way around.

### Cover every branch (`--history` follows the current branch only)

```bash
for ref in $(git for-each-ref --format='%(refname:short)' refs/heads refs/tags); do
  git checkout -q --detach "$ref"
  echo "== $ref =="
  leakpulse scan . --history 500 --quiet || echo "!! findings at $ref"
done
git checkout -q main
```

Run it on a clean worktree; `git stash` first if you have local changes.

---

## T+9: prevention — put the check before the commit

The most common second incident is "we added a rule but nobody runs it". A gate needs two properties: **on by default** and **fail closed**.

### Option 1: pre-commit (local, fastest feedback)

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/stackpulse-lab/leakpulse
    rev: v0.4.0
    hooks:
      - id: leakpulse          # staged changes only, blocks the commit
      - id: leakpulse-worktree # whole tree, no history
```

```bash
pipx install pre-commit
pre-commit install
pre-commit run --all-files
```

No pre-commit? Use the built-in hook:

```bash
leakpulse install-hook
```

Measured blocking behavior (stage a fake GitHub token, then commit):

```console
$ git commit -m "oops"
HIGH   github-token  bad.py:1  ghp_****************1234  GitHub token (classic app/OAuth/refresh)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 1 file in 0.01s.
$ echo $?
1
```

The commit is rejected, the file stays staged, and you fix it before retrying.

> The hook is **fail-closed**: if `leakpulse` is not on `PATH`, it fails instead of silently allowing the commit.
> With a virtualenv, activate it before committing, or set `LEAKPULSE_SRC` inside the hook.

### Option 2: CI gate + Code Scanning (team, cannot be skipped)

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

- `history: "100"` lets CI catch secrets that were committed once and removed later;
- `continue-on-error: true` plus `if: always()` keeps the SARIF report flowing into the Security tab even when the gate fails;
- to observe before enforcing, set `fail-on: never` for a week, then tighten it.

### Three cheap policies

1. **Allow test fixtures explicitly**: append `# leakpulse:allow` to the line instead of excluding all of `tests/`.
2. **Placeholders only in examples**: `.env.example` should say `your-key-here`, never a real value with one character changed.
3. **Rotate on a schedule**: put quarterly rotation on the calendar. Leaks are passive; rotation is active.

---

## T+10: postmortem checklist (copy into your incident template)

- [ ] Credential revoked/rotated server-side; replacement verified working
- [ ] Call logs exported and reviewed for unusual sources or volume
- [ ] Scope confirmed: files, commits, branches, public or private
- [ ] Blast radius assessed: permissions, data, customers, obligations
- [ ] Evidence archived: commit ids, reports (JSON/SARIF/HTML), timeline
- [ ] Local hook or CI gate enabled and actually tested against a real block
- [ ] History rewrite scheduled, or explicitly declined with a recorded reason
- [ ] Write-up filed so the next drill has a baseline

---

## Appendix: the 10-minute command card

```bash
# 1) Forensics: worktree + last 500 commits
leakpulse scan . --history 500

# 2) Three deliverables
leakpulse scan . --history 500 --format json  --output leak.json
leakpulse scan . --history 500 --format sarif --output leak.sarif
leakpulse scan . --history 500 --format html  --output leak.html

# 3) Local gate
leakpulse install-hook

# 4) Self-check
leakpulse scan . --history 0 --fail-on high
```

LeakPulse is MIT-licensed, has zero third-party dependencies, and runs entirely locally: no network, no uploads, no telemetry. It cannot tell whether a key is still valid, and it is not a SAST replacement — **rotate on discovery** is the most important advice it can give.

---

*Repository: <https://github.com/stackpulse-lab/leakpulse> · Questions and ideas: open an issue.*
