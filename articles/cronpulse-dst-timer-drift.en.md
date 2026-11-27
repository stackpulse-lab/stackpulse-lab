# When the schedule did not run: a DST gap, a duplicated backup, and systemd timer drift

> Field notes from a New York node: one daily backup silently skipped in spring,
> ran twice in autumn, and after a migration to systemd a set of timers had
> drifted from the inventory nobody owned. Every command and exit code below was
> run locally; the unit files are reproductions, not real host data.

## 1. The incident: a backup that vanished, then a backup that ran twice

Monitoring reported on the second Monday of March: **Sunday's 02:30 full backup
is missing**. There was no `failed` line in the logs. The service had succeeded —
because it was never started.

The same configuration, on the first Sunday of November, produced **two copies of
the same backup**. The downstream reconciliation job was not idempotent and
issued a duplicate invoice.

Neither was a typo. Both were DST:

- On 2026-03-08 the US Eastern zone moves `02:00 → 03:00`, so **02:30 does not exist**.
- On 2026-11-01 the clock falls back, so **01:00 and 01:30 each happen twice**.

Classic cron matches wall-clock time. A daemon typically skips a nonexistent
instant without an error, so "the job did not run" is only visible when the
downstream report is empty.

## 2. Layer one: print the times that do not exist

```console
$ cronpulse next "30 2 * * *" --tz America/New_York --after 2026-03-07T12:00 -n 2
30 2 * * *  (after 2026-03-07T12:00:00-05:00)
 1. 2026-03-09 02:30:00-04:00
 2. 2026-03-10 02:30:00-04:00
note: skipped 1 wall-clock time(s) that do not exist (DST gap): 2026-03-08 02:30:00
$ echo $?
0
```

**The exit code is 0**, because the expression is valid and the job does fire on
other days. This class of bug cannot be found by "the command failed"; it is only
visible in the `note:` line. With `--json` the same facts land in `dst.skipped`,
which is what you want in a daily report.

The autumn overlap is the mirror image — one wall-clock time maps to two real
instants:

```console
$ cronpulse next "*/30 1 * * *" --tz America/New_York --after 2026-10-31T23:30 -n 4
*/30 1 * * *  (after 2026-10-31T23:30:00-04:00)
 1. 2026-11-01 01:00:00-04:00
 2. 2026-11-01 01:30:00-04:00
 3. 2026-11-01 01:00:00-05:00
 4. 2026-11-01 01:30:00-05:00
note: 2 wall-clock time(s) occur twice (DST overlap), both listed: 2026-11-01 01:00:00, 2026-11-01 01:30:00
```

The `-04:00` / `-05:00` offsets are the proof that these are two real runs.
Idempotency keys must be built on UTC timestamps, not on a local `01:00`.

`cronpulse explain` also states where the timezone comes from, which kills the
"I thought cron honoured `CRON_TZ`" assumption:

```console
$ cronpulse explain "30 2 * * *"
expression : 30 2 * * *
fields     : minute=30; hour=2; day-of-month=*; month=*; day-of-week=*
hint       : cron daemons run in the system timezone; classic Vixie cron also honours a per-crontab CRON_TZ=<IANA zone> line, systemd timers ignore CRON_TZ (use OnCalendar with its own DST rules). Preview another zone with --tz.
```

The important part: **systemd timers ignore `CRON_TZ` entirely**. Mixing host
timezone, `CRON_TZ`, and `OnCalendar=` is how "the preview said one thing and
production did another" happens.

## 3. Layer two: timer inventory drift

The backup later moved from cron to a systemd timer. After a migration script, a
manual hotfix, and a merge, `/etc/systemd/system/*.timer` no longer matched the
inventory the team believed in.

Reproduction host (five timers under `units/`):

- `backup.timer`: inventory says `daily`, the unit says `Mon 09:00`;
- `report.timer`: only `Mon..Fri 09:00` left, the `Fri 18:00` entry is gone;
- `audit.timer`: `OnBootSec=15min` + `OnUnitActiveSec=1d` — a **relative** timer;
- `legacy-sweep.timer`: `OnCalendar=*-02-30 00:00`, and February has no 30th;
- `dup.timer`: a merge left two identical `OnCalendar=hourly` lines.

The manifest `timers.json` declares what should exist:

```json
{
  "timers": [
    {"name": "backup.timer", "calendar": "daily", "service": "backup.service"},
    {"name": "report.timer", "calendars": ["Mon..Fri 09:00", "Fri 18:00"]},
    {"name": "legacy-sweep.timer", "calendar": "*-02-30 00:00", "service": "legacy-sweep.service"}
  ]
}
```

The first comparison refuses to guess about relative timers:

```console
$ cronpulse timer-drift units --expect timers.json
cronpulse: units/audit.timer:5: OnBootSec= is a relative timer with no fixed calendar; pass --allow-relative to skip it
$ echo $?
2
```

That is deliberate: `OnBootSec` has no fixed calendar, and silently skipping it
would produce a false "all green". Once those timers are monitored elsewhere,
opt out explicitly:

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

Four leads in one report:

1. **missing**: in the manifest, absent on disk — the Friday 18:00 report really was gone;
2. **changed**: `backup.timer` became `Mon 09:00`, turning "nightly" into "weekly";
3. **unexpected**: `dup.timer` appears twice because the unit repeats `OnCalendar=`;
4. **warning**: `*-02-30` can never fire within the 8-year horizon.

### A detail that causes false alarms: `Unit=` is part of identity

Look at `report.timer: calendar unchanged (service - -> report.service)`. The
calendars are identical, so why `changed`? Because the manifest omitted `service`
while the unit sets `Unit=report.service`. **Identity = name + service target +
calendar.** Retargeting a timer is not "the same job at a new time"; it is a
different service.

Lesson: always write `service` in the manifest, or the first rollout will show a
"changed but the calendar did not change" line and the team will dismiss the tool
as noisy.

## 4. Verifying the fix: exit 4 to exit 0

Fix the units (restore `daily`, add `Fri 18:00`, drop the duplicate and the
never-firing timer) and add `service` to the manifest:

```console
$ cronpulse timer-drift fixed2 --expect timers.fixed.json --allow-relative
actual: 3 timer calendars; expected: 3; matched: 3
no drift: timer units match the expected manifest
$ echo $?
0
```

Run the same check **without** `--allow-relative` and it still fails with `2`:

```console
$ cronpulse timer-drift fixed2 --expect timers.fixed.json
cronpulse: fixed2/audit.timer:5: OnBootSec= is a relative timer with no fixed calendar; pass --allow-relative to skip it
$ echo $?
2
```

That is not a regression. It is a reminder that relative timers can only be
skipped explicitly. Keeping this failing variant in CI stops someone from
quietly adding `--allow-relative` to every script.

## 5. Wiring it into a daily check and CI: route by exit code

| Exit | Meaning | Suggested action |
| --- | --- | --- |
| `0` | in sync / preview succeeded | record |
| `2` | invalid expression, unreadable file, relative timer not opted out | config error, fix now |
| `3` | cannot fire within 8 years | invalid schedule, fix now |
| `4` | drift or warnings | compare manifest, triage missing/changed |

Compress the JSON in a daily check so the totals come first:

```console
$ cronpulse timer-drift units --expect timers.json --allow-relative --json \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print("drift={} missing={} unexpected={} changed={} duplicates={} never_fires={}".format(d["drift"], len(d["missing"]), len(d["unexpected"]), len(d["changed"]), len(d["duplicates"]), len(d["never_fires"])))'
drift=True missing=1 unexpected=2 changed=2 duplicates=1 never_fires=1
$ echo ${PIPESTATUS[0]}
4
```

Mind `${PIPESTATUS[0]}`: the pipe makes `python3` the last command, so its exit
code is 0. The code you care about is `cronpulse`'s `4`. Use `set -o pipefail`,
or write the JSON to a file first and parse it afterwards.

The DST side is the same: `cronpulse next` keeps exit code 0 while reporting
`note:` / `dst.skipped`, so a check must inspect those fields rather than only
the exit code:

```console
cronpulse next "30 2 * * *" --tz America/New_York --after "$(date -Iseconds)" -n 3 --json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("upcoming:", len(d["runs"]), "skipped:", len(d.get("dst",{}).get("skipped",[])), "ambiguous:", len(d.get("dst",{}).get("ambiguous",[])))'
```

## 6. Post-incident checklist

1. **Keep critical jobs out of the 02:00–03:00 local window.** Nearly every DST
   zone skips or repeats that hour. For cross-region stability, use UTC or a
   time after 04:00.
2. **"The command succeeded" is not "the job ran."** A job in a DST gap produces
   no failure log. Preview the next three runs with `--tz` and read `note:` /
   `dst.skipped`.
3. **Make idempotency keys UTC-based.** In autumn the local `01:00` happens
   twice; deduplicating on local time always drops the second run.
4. **Put the timer inventory in Git.** Review `timers.json` together with the
   unit files so a migration script's changes show up in the diff.
5. **Write `Unit=` explicitly.** It is part of the timer's identity; omitting it
   from the manifest creates `changed` noise on the first run.
6. **Handle relative triggers explicitly.** `OnBootSec=` / `OnUnitActiveSec=`
   have no fixed calendar: either pass `--allow-relative` and monitor them
   elsewhere, or convert them to a fixed `OnCalendar=`.
7. **Drop-ins are not merged.** If you rely on `*.timer.d/` overrides, point
   `timer-drift` at the concrete unit file; otherwise it compares the base file,
   not the effective configuration.
8. **Keep CI strict.** Grant `--allow-relative` only to known relative timers;
   leave every other path without it so exit code 2 keeps blocking mistakes.

## 7. Real exit codes from this run

| Command | Exit code |
| --- | --- |
| `next "30 2 * * *" --tz America/New_York` (DST gap) | `0` + `note: skipped 1` |
| `next "*/30 1 * * *" --tz America/New_York` (DST overlap) | `0` + 4 real instants |
| `explain "30 2 * * *"` | `0` + `CRON_TZ` hint |
| `timer-drift units` (relative timer present) | `2` |
| `timer-drift units --allow-relative` (drift) | `4` |
| `timer-drift fixed2 --allow-relative` (after fix) | `0` |
| `timer-drift fixed2` (strict mode) | `2` |
| `calendar "*-02-30 00:00"` | `3` |
| `check "0 0 30 2 *"` | `3` |

Tool: `pip install cronpulse-cli` (command `cronpulse`; zero third-party
dependencies, no network, no state on disk). Every unit, manifest, and command
in this article can be reproduced locally.
