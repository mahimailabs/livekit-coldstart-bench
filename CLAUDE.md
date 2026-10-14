# CLAUDE.md

Benchmark of LiveKit agent cold starts and call draining across serverless platforms.

- `agent/`: the benchmark agent. `agent.py` is the registered-worker shape, `oneshot.py` the one-call-per-container shape; both share `core.py`.
- `harness/`: `bench.py` measures runs into JSONL, `summarize.py` makes the table, `triggers.py` holds per-platform triggers.
- `platforms/`: deploy files per platform. Build images with `--platform linux/amd64`.
- Pin exact dependency versions. Run `pre-commit run --all-files` before committing.
- Commits: author mahimairaja, signed, no AI attribution. Branches start with feat/, fix/ or chore/.
- Never commit credentials. Platform secrets live in each platform's secret store.

## Platform docs

Check the vendor docs before deploying anything. The docs MCP servers are in `.mcp.json` (remote, no credentials): `livekit-docs`, `cerebrium-docs`, `aws-knowledge` (AWS docs, AgentCore, regional availability) and `microsoft-learn` (Azure).

- Modal has no docs MCP. Read https://modal.com/llms.txt.
- Google Cloud's official docs MCP (https://developerknowledge.googleapis.com/mcp) needs an API key, so it isn't configured here. Use context7 or https://cloud.google.com/run/docs.
