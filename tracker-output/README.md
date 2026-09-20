# tracker-output

Phone-readable output of the [lowcap-call-tracker](../skills/lowcap-call-tracker/) skill.

| File | Written by | Cadence |
|---|---|---|
| `stats.md` | `skills/lowcap-call-tracker/scripts/run_cycle.py` | every run (every 4 hours) |
| `improvements.md` | `skills/lowcap-call-tracker/scripts/learning_loop.py` | weekly, proposals only |

These two files are **tracked and pushed** by the VPS deployment
(`run_cycle.py --git-push`) so results are readable from GitHub on a phone.
Everything else the tracker produces — per-run JSON, the SQLite database — stays
local under `reports/` and `state/`, both of which are gitignored.

`improvements.md` is a proposal list. Nothing in it is applied automatically.
