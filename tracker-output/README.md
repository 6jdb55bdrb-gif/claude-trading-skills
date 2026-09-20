# tracker-output

Phone-readable output of the [lowcap-call-tracker](../skills/lowcap-call-tracker/) skill.

| File | Written by | Cadence |
|---|---|---|
| `stats.md` | `skills/lowcap-call-tracker/scripts/run_cycle.py` | every run (every 4 hours) |
| `improvements.md` | `skills/lowcap-call-tracker/scripts/learning_loop.py` | weekly, proposals only |
| `state_snapshot.json` | `skills/lowcap-call-tracker/scripts/state_snapshot.py` | every scheduled run |

These two files are **tracked and pushed** by the VPS deployment
(`run_cycle.py --git-push`) so results are readable from GitHub on a phone.
Everything else the tracker produces — per-run JSON, the SQLite database — stays
local under `reports/` and `state/`, both of which are gitignored.

`improvements.md` is a proposal list. Nothing in it is applied automatically.

`state_snapshot.json` is the tracker's database as JSON. A run on a machine with
a real disk keeps its state in `state/lowcap_calls.db` and ignores this file; a
run on a throwaway checkout (a scheduled cloud session) imports the snapshot into
its empty database and rewrites it afterwards, which is what keeps dedupe and PnL
history continuous. It is also the migration path to a server:

```bash
python3 skills/lowcap-call-tracker/scripts/state_snapshot.py \
  --import tracker-output/state_snapshot.json
```
