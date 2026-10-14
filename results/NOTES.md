# First results: notes (2026-10-14)

Harness host: Mac (arm64) in Sarnia, Ontario. LiveKit project `bench` on the Build plan; the worker
registered in region "Canada" from the Mac, "us-east" from LiveKit Cloud and "US East B" from
Cerebrium. Light agent only, except the Modal `*_heavy*` runs. Spend: Modal $1.02, Cerebrium
well under $0.10 (about 15 min at 2 vCPU / 4 GB), LiveKit Cloud $0 (Build plan).

## Per-step medians (seconds after the trigger)

Agent timestamps come from the agent's clock, harness timestamps from the Mac's clock (both NTP).

| Platform | Label | Runs ok | Process start | Imported | Job received | Connected | First audio |
|---|---|---|---|---|---|---|---|
| mac-worker | warm | 20/20 | warm | warm | 0.08 | 0.47 | 0.55 |
| lk-cloud | warm | 20/20 | warm | warm | 0.15 | 0.52 | 0.58 |
| cerebrium | warm | 20/20 | warm | warm | 0.15 | 0.38 | 0.44 |
| modal run_call | cold | 20/20 | 1.73 | 4.04 | 4.06 | 4.35 | 4.44 |
| modal run_call_snap | cold | 20/20 | (snapshot) | (snapshot) | 2.79 | 3.19 | 3.36 |
| modal run_call_heavy | cold-heavy | 10/10 | 1.22 | 7.59 | 7.61 | 8.01 | 8.09 |
| modal run_call_heavy_snap | cold-heavy | 10/10 | (snapshot) | (snapshot) | 4.37 | 4.96 | 5.25 |
| modal run_call | warm (gap 0) | 20/20 | mixed | mixed | 3.55 | 3.90 | 4.01 |

"warm" means the process started before the trigger. On snapshot functions, `process_start` and
`imported` are restored from the snapshot, so they predate the trigger. Only `job_received` and
later are meaningful there.

## Findings

1. **LiveKit Cloud Build plan: 5 concurrent sessions, and extra dispatches queue (they aren't
   dropped).** On the first warm attempt each session stayed open about 30 s after the caller
   left, waiting for the room to close. At a 5 s gap that put 6 sessions in flight. Runs 6 onward
   got their job about 2 min late and timed out (`warm-v0-throttled`). Self-hosted livekit-server
   drops these instead (see README). Fix: the agent calls `ctx.shutdown()` when the caller
   leaves, and the harness deletes the room after each run. Both are in this branch.
2. **LiveKit Cloud never scaled to zero in 40 min.** After the last session the agent stayed
   `Running`, 1/1/1 replicas, polled every 30 s from 01:30 to 02:10 UTC. A call after 40 min idle
   was warm (first audio 0.51 s, `idle-40m`). The docs say Build plan agents "can be" scaled to
   zero and that a cold start adds 10-20 s, but give no idle threshold. That leaves 0 cold runs
   for LiveKit Cloud.
3. **Cerebrium cannot scale a registered LiveKit worker from zero.** `min_replicas = 0` with
   `cpu_utilization` scaling is rejected at deploy: "Min replicas must be greater than 0 for CPU
   and Memory scaling". The request-based metrics need HTTP traffic through Cerebrium, and a
   worker that dials out to LiveKit gets none. So that shape has no cold path: it's always-on or
   unreachable. No cold runs.
4. **Cerebrium redeploy drained the call.** A 600 s hold call survived a redeploy triggered 58 s
   in: 599 ticks, last tick at 599.1 s, `survived: true`. The new version was live 21 s after the
   deploy started.
5. **Modal cold start is about 4.4 s, and imports are half of it.** Container start takes 1.7 s
   after `spawn`, then Python imports (livekit + livekit-agents) take 2.3 s. Memory snapshots
   save about 1.1 s light and 2.8 s heavy at p50. The p90s are noisy: snap light 6.2 s, heavy
   13.7 s. Each snapshot build cost about 8-9 s on its first two runs.
6. **The Modal "warm" batch (gap 0) is not warm with this config.** Only 8/20 calls reused a
   container. With one input per container, the next call arrives while the previous container
   is still in the agent's 2 s "caller left" grace period, so Modal starts a new container
   (cold) or queues behind the old one (about 2.0 s). True warm reuse (container already idle)
   gave 0.46-0.65 s first audio. A real warm number needs a gap of 3-5 s, or `min_containers`.
7. **Bug fixed after the Modal runs: oneshot containers lingered.** Once the harness started
   deleting rooms, `run_in_room` kept ticking into a disconnected room, because the participant
   list never emptied. Modal containers stayed busy until the function timeout. 63 were still
   running when the app was stopped, which is most of the $1.02. The loop now exits when the
   room disconnects (verified locally). This doesn't change any first-audio number, but it
   contributed to finding 6.
8. **Mac baseline outlier.** 1 of 20 local runs took 5.8 s: the dispatch reached the worker
   5.2 s late (server side). The other 19 were at most 0.83 s.

## Deviations from the plan

- The local worker on macOS has no `/proc`, so its `process_start` falls back to the job time.
- Cerebrium and LiveKit Cloud share agent name "bench" in one project. Cerebrium ran with
  `LIVEKIT_AGENT_NAME_OVERRIDE=bench-cerebrium`, set as an ENV in the staged Dockerfile copy used
  for that deploy only. The harness used `BENCH_AGENT_NAME=bench-cerebrium`.
- `platforms/modal_app.py`: the heavy image installs `requirements.txt` and then the heavy
  extras, because Modal can't resolve the `-r requirements.txt` line.
- Snapshot functions got 2 extra `snapshot-build` runs ahead of the full 20 (or 10) cold runs.
