# CLAUDE.md

Benchmark of LiveKit agent cold starts and call draining across serverless platforms.

- `agent/`: the benchmark agent. `agent.py` is the registered-worker shape, `oneshot.py` the one-call-per-container shape; both share `core.py`.
- `harness/`: `bench.py` measures runs into JSONL, `summarize.py` makes the table, `triggers.py` holds per-platform triggers.
- `platforms/`: deploy files per platform. Build images with `--platform linux/amd64`.
- Pin exact dependency versions. Run `pre-commit run --all-files` before committing.
- Commits: author mahimairaja, signed, no AI attribution. Branches start with feat/, fix/ or chore/.
- Never commit credentials. Platform secrets live in each platform's secret store.
