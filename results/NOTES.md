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
5. **Modal cold start is about 4.4 s, and most of it is Modal's own startup.** p50 steps after
   `spawn`: container start 1.73 s, Modal runtime and app load 1.85 s, agent imports (livekit +
   livekit-agents) 0.46 s, connect 0.31 s, first audio 0.09 s. Memory snapshots
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

# Round 2: notes (2026-10-14)

Same harness host and LiveKit project. Images were built on AWS CodeBuild (amd64 and arm64) and
copied to Artifact Registry with `crane`, because local Docker pulls hung on a credential-helper
Keychain prompt and `gcloud builds submit` returned PERMISSION_DENIED for a project Owner.
Spend: well under $1 (Cloud Run and Fargate about 15 min each at 2 vCPU / 4 GB, CodeBuild about
10 min, Modal a few cents). Everything created in AWS and GCP was deleted afterwards.

## Per-step medians (seconds after the trigger)

| Platform | Label | Runs ok | Imports start | Imported | Job received | Connected | First audio |
|---|---|---|---|---|---|---|---|
| modal run_call | warm-gap5 | 20/20 | warm | warm | - | - | 0.67 |
| cloudrun-job | cold | 10/10 | 27.19 | 28.55 | 28.55 | 29.05 | 29.10 |
| cloudrun-pool | warm | 20/20 | warm | warm | 0.16 | 0.35 | 0.43 |
| agentcore | cold (new session) | 20/20 | pre-booted | pre-booted | 0.67 | 0.98 | 1.01 |
| agentcore | warm (same session) | 21/21 | warm | warm | 0.24 | 0.55 | 0.58 |
| fargate | warm | 20/20 | warm | warm | 0.14 | 0.36 | 0.41 |

The Cloud Run Job and AgentCore triggers go through `gcloud run jobs execute --async` and boto3
`invoke_agent_runtime` (on a thread). Their client-side overhead is included.

## Findings

1. **Modal warm needs a gap longer than the agent's 2 s grace period.** At a 5 s gap, with the
   linger fix, 20/20 calls reused one of 2 containers: p50 0.67 s, p90 0.88 s (round 1 at gap 0
   was 4.01 s).
2. **Cloud Run Jobs are not usable per call: 29 s to first audio.** The container starts about
   27 s after `jobs execute`. Imports (1.1 s) and connecting (0.5 s) are noise next to that.
   Under the Cloud Run sandbox `/proc` gives a wrong process start (about 9 min before the
   trigger), so `import_start` is used instead.
3. **The Cloud Run worker pool is the fastest warm path** together with Fargate: join 0.20 s,
   first audio 0.43 s.
4. **A Cloud Run worker pool redeploy drops the call for about 23 s.** Run twice. The old
   instance logs "Shutting down user disabled instance" and the worker starts draining, then
   the caller hears 22.9 s of silence. LiveKit then re-dispatches the job to the new revision
   (`agent_joins: 2`), which plays a fresh greeting. The tick count (472-480 in 300 s, against
   about 278-300 for one agent) suggests the old agent may come back or overlap. This needs
   per-track tick logging to confirm.
5. **AgentCore keeps pre-booted microVMs.** A new session (new `runtimeSessionId`) got first
   audio at p50 1.01 s, but the process in it had imported about 69 s before the invoke, with
   19 distinct processes for 20 sessions. So "cold" here means routing to a pre-initialized
   microVM, not a boot. The very first invoke after the runtime was created took 1.64 s.
   Reusing one session gave 0.58 s.
6. **A Fargate rolling update drops the call for about 21 s.** On SIGTERM the worker drains
   (drain timeout 3600 s), but ECS stops the task after its 30 s `stopTimeout`. LiveKit
   re-dispatches the same job ID to the new task: 21.2 s gap, `agent_joins: 2`, 278 ticks.
   Getting a real drain needs a `stopTimeout` raised to its 120 s maximum, which is still
   shorter than a long call.
7. The drain rows' agent timestamps come from the second (re-dispatched) agent, because its
   timings packet replaces the first one.

## Deviations

- AgentCore received the LiveKit credentials as runtime environment variables. AgentCore has no
  native secret injection, and the runtime was deleted after the runs. Fargate used Secrets
  Manager, and Cloud Run used Secret Manager.
- The AgentCore warm and cold triggers use boto3 with the `crt` extra, which the `aws login`
  credential provider needs (`boto3[crt]==1.43.113`).
- Fargate ran x86_64 (same image as Cloud Run); AgentCore runs arm64 (required).
- Hold runs were 300 s, not 600 s.
