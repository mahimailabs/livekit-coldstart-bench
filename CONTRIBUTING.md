# Adding a platform

The agent stays the same everywhere. A new platform only needs a way to run it and a way to start it.

## 1. Pick the shape

| Shape | Entry point | Use it when |
| --- | --- | --- |
| Registered worker | `python agent.py start` | the platform runs a long-lived process (a service, worker pool or VM) |
| One container per call | `python oneshot.py --room X` (or `run_call(room)`) | the platform starts a process per request (functions, jobs, sandboxes) |

Both use `agent/core.py`. Don't change the agent for a platform. If the platform needs a wrapper, put it next to its deploy files, like `platforms/agentcore/app.py`.

## 2. Add the deploy files

Create `platforms/<name>/` with whatever the platform needs: a config file, a wrapper, deploy commands in a short README. Rules:

- Build images for `linux/amd64` (`platforms/Dockerfile`), unless the platform requires ARM64, like AgentCore.
- Pin every version.
- Keep LiveKit credentials in the platform's own secret store. Never put them in the repo.
- Set `BENCH_PLATFORM=<name>`, so the agent reports where it ran.
- If another worker shares the LiveKit project, set `LIVEKIT_AGENT_NAME_OVERRIDE=bench-<name>` on the worker and `BENCH_AGENT_NAME=bench-<name>` in the harness.

## 3. Add a trigger, if needed

Workers use the `dispatch` trigger, and any CLI works through `command`:

```sh
BENCH_COMMAND='mycloud run lk-bench --env BENCH_ROOM={room}' python harness/bench.py --trigger command ...
```

If the platform has an SDK, add an async function to `harness/triggers.py` and register it in `TRIGGERS`. The function must start the agent for one room and return without waiting for the call to end. Import the SDK inside the function.

## 4. Run it

From `harness/`, with `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` exported:

```sh
# warm: keep the gap longer than the agent's 2 s grace period after the caller leaves
python bench.py --platform <name> --trigger dispatch --label warm --runs 20 --gap 5 --out ../results/<name>.jsonl

# cold: wait long enough for the platform to scale to zero between runs
python bench.py --platform <name> --trigger <trigger> --label cold --runs 20 --gap <seconds> --out ../results/<name>.jsonl

# redeploy during a call: start this, then redeploy the platform about 60 s in
python bench.py --platform <name> --trigger dispatch --label drain-redeploy --runs 1 --hold 300 --out ../results/<name>.jsonl

python summarize.py ../results/<name>.jsonl
```

Check that the agent's timings arrived (`agent` in each row). For cold runs, check that `agent.process_start` or `agent.import_start` is after `t_trigger`. If it isn't, the platform reused a warm process, and the run isn't cold.

## 5. Write it up and open a PR

- Add the platform to the TL;DR table in `README.md`, and to `results/NOTES.md` with the per-step medians and anything surprising.
- If it changes the picture, update the hero data in `docs/assets/src/hero.html` and rerender (`node render.mjs` there).
- Tear down everything you created, and say in the PR roughly what it cost.
- Run `pre-commit run --all-files`. Branches start with `feat/`, `fix/` or `chore/`.

The open list is in [ROADMAP.md](ROADMAP.md) and the pinned roadmap issue.
