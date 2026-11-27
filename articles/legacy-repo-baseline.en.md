# Adopting a secret scanner in a legacy repo: 10 minutes with baseline mode

> For teams with years of history that want a real pre-merge gate, not another red job
> nobody reads. Commands and exit codes below were run locally; demo credentials are
> random values generated at runtime and all output is redacted.

## Why secret scanners die in legacy repos

A greenfield repo is easy: the first scan is clean. A legacy repo is not.

You add `gitleaks`, `trufflehog` or `leakpulse` to CI and the first run returns dozens
of `HIGH` findings:

- fake AWS keys in three-year-old fixtures;
- rotated GitHub tokens that still live in history;
- `sk-...` placeholders in sample configs;
- webhooks for services that were decommissioned.

Nobody fixes all of that in one day. To ship, the team either adds ignore rules or
deletes the step. Either way, **the next real leak also goes unnoticed**.

The bottleneck is not rule coverage but the adoption path: a legacy repo needs a
reviewable, shrinking "known set", and CI should only fail on **new** findings.

That is what LeakPulse v0.5.0 baseline mode does.

## What the baseline actually contains

`leakpulse scan --write-baseline FILE` writes a fingerprint snapshot:

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

Each fingerprint is the first 20 hex chars of SHA-256 over `rule id + path + matched
value`. Consequences:

- **No credential and no masked fragment** is stored, so the file is safe to commit,
  paste into a PR and hand to a reviewer.
- **No line numbers**: moving code around keeps old findings suppressed.
- **Path is part of the fingerprint**: renaming or moving a file with a secret is
  treated as new — a common way to slip past review.
- **Value is part of the fingerprint**: after rotation the old fingerprint stops
  matching and a new one appears, so CI fails again. That is the point.

A baseline is a reviewed inventory of existing debt, not a mute button.

## The 10-minute rollout (real terminal transcript)

Requirements: Python 3.9+ and git. The demo repo has a `legacy.py` from a 2019
migration with a hardcoded fake DeepSeek key on line 2 (generated at runtime).

### Step 1 — see what is already there (this command fails, expected)

```console
$ leakpulse scan . --history 20
HIGH   deepseek-key  legacy.py:2  sk-C****************VNPk  DeepSeek API key (sk-…, same shape as OpenAI keys)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 2 files and 1 commit in 0.01s.
$ echo $?
1
```

`--history 20` also scans the last 20 commits, so "committed once, then deleted" is
still caught.

### Step 2 — write the baseline (this command always exits 0)

```console
$ leakpulse scan . --history 20 --write-baseline leakpulse-baseline.json
leakpulse: recorded 1 fingerprint(s) in leakpulse-baseline.json
HIGH   deepseek-key  legacy.py:2  sk-C****************VNPk  DeepSeek API key (sk-…, same shape as OpenAI keys)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 2 files and 1 commit in 0.01s.
$ echo $?
0
```

Two details matter:

1. It **still prints the full report**, so you can triage before committing the
   snapshot — some of these might deserve rotation today, not suppression.
2. It always exits `0`, because snapshotting is not a verdict on the repository.
   The verdict happens in the next step.

Review and commit the snapshot:

```bash
git add leakpulse-baseline.json
git commit -m "chore: record known leakpulse findings"
```

### Step 3 — fail only on new findings

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
No potential secrets found. Scanned 3 files and 1 commit in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
0
```

CI is green now — with no rule disabled.

### Step 4 — prove that it still catches new leaks

Add a file with a fake GitHub token (also generated at runtime):

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
HIGH   github-token  fresh.py:1  ghp_****************71fT  GitHub token (classic app/OAuth/refresh)

1 potential secret found (1 high, 0 medium, 0 low) Scanned 4 files and 2 commits in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
1
```

The JSON output separates new findings from suppressed ones, which is handy for
triage scripts:

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json --format json \
    | python3 -c "import json,sys;d=json.load(sys.stdin);print('findings:',[f['path'] for f in d['findings']],'baseline:',d['baseline'])"
findings: ['fresh.py'] baseline: {'file': 'leakpulse-baseline.json', 'suppressed': 1}
```

### Step 5 — check the two boundaries people get wrong

**Moving a line does not re-report.** Insert two blank lines at the top of
`legacy.py`; the key moves from line 2 to line 4:

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
... 1 known finding suppressed by baseline.
$ echo $?
1        # the only failure is fresh.py from step 4, not the old legacy.py
```

**Rotating a key does re-report.** Replace the old value in `legacy.py`:

```console
$ leakpulse scan . --history 20 --baseline leakpulse-baseline.json
HIGH   github-token  fresh.py:1    ghp_****************71fT  ...
HIGH   deepseek-key  legacy.py:4  sk-q****************XRrv  ...

2 potential secrets found (2 high, 0 medium, 0 low) Scanned 4 files and 2 commits in 0.01s. 1 known finding suppressed by baseline.
$ echo $?
1
```

The old fingerprint pins the old value, so the new value is necessarily new. This is
exactly the "rotated the key, forgot the config, committed it again" accident.

## Wiring it into CI

### GitHub Actions (zero-config)

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
          fetch-depth: 200        # history scanning needs commits
      - uses: stackpulse-lab/leakpulse@v0.5.0
        with:
          history: "200"
          baseline: leakpulse-baseline.json
          fail-on: high
```

`fetch-depth` must be greater than 1, otherwise `--history` only sees the last
commit. The Action installs from the tag you reference — no PyPI, no
`setup-python`.

### Any other CI or local shell

```bash
pip install leakpulse==0.5.0
leakpulse scan . --history 200 --baseline leakpulse-baseline.json --fail-on high
```

With SARIF, new findings can go straight to GitHub Code Scanning:

```bash
leakpulse scan . --history 200 --baseline leakpulse-baseline.json \
  --format sarif --output leakpulse.sarif
```

### Relationship to pre-commit

Baseline covers history and CI; the hook covers the commit. Use both:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/stackpulse-lab/leakpulse
    rev: v0.5.0
    hooks:
      - id: leakpulse          # staged files only, no baseline needed
```

Staged scanning is incremental by nature, so it needs no baseline. The baseline is
for whole-tree plus history jobs.

## Operating rules so the baseline does not rot

Treat the baseline as an asset with an expiry date:

1. **Someone else reviews it.** A snapshot must be reviewed by someone other than
   the author, especially `HIGH` entries. Never use `--write-baseline` to turn a red
   job green without reading it.
2. **Open rotation tickets.** Being in the baseline is not "safe". For each legacy
   finding, file a rotation task; after rotation the fingerprint expires, the scan
   reports once, then you drop the old entry.
3. **Keep it per branch.** Release branches have different legacy sets. Commit the
   baseline with the code; never stash it in a CI cache.
4. **Shrink it quarterly.** Regenerate with `--write-baseline` and compare `count`.
   The number should go down; an increase means someone is parking new problems in
   the baseline.
5. **Pin the history depth.** Use the same `--history N` for writing and using the
   baseline. Jumping from 50 to 200 surfaces more history — new discoveries, not
   regressions.
6. **Path changes count as new.** A rename invalidates the baseline by design;
   confirm it is the same debt, then refresh the snapshot.

## Pitfalls from this experiment

- **Temporary files are part of the worktree.** My first attempt left the JSON file
  containing the generated fake secrets inside the demo repo, so it produced two
  extra `HIGH` findings (`github-token` + `openai-key`). Keep demo material outside
  the repo, or the baseline records entries that should never exist.
- **One string can match several rules.** An `sk-` key fits both `openai-key` and
  `deepseek-key`; LeakPulse reports only the most specific one because `deepseek-key`
  comes first. If you write your own rules, order matters or one leak becomes noise.
- **`--write-baseline` always exits 0.** Do not use it as a gate; only `--baseline`
  belongs in the pipeline.
- **The two flags are mutually exclusive.** Passing both exits `2` instead of
  guessing whether to read or write.

## 10-minute checklist

```text
[ ] leakpulse scan . --history 200                     # see the debt, expect exit 1
[ ] leakpulse scan . --history 200 --write-baseline …  # snapshot, review the diff
[ ] git add leakpulse-baseline.json && git commit
[ ] leakpulse scan . --history 200 --baseline …        # confirm exit 0
[ ] add a fake key and confirm exit 1 (do not commit it)
[ ] add the Action to CI with fetch-depth: 200
[ ] file rotation tickets for every HIGH, not just a baseline entry
```

## Takeaway

Adoption of secret scanning rarely fails because nothing is detected; it fails
because too much is detected at once and the team disables the check. Baseline mode
splits adoption into two steps: **turn known debt into a reviewable fingerprint
inventory, then let CI fail only on new findings.** Nothing is hidden — rotation,
renames and new files all report again — the historical debt is just handled
separately from today's mistakes.

MIT, zero dependencies, runs locally: <https://github.com/stackpulse-lab/leakpulse>

```bash
pip install leakpulse==0.5.0
```
