# livekit-coldstart-bench

Deploy one identical LiveKit agent on every platform and measure what the caller feels.

The agent plays a 1 s tone the moment it joins, then a 100 ms tick every second. There is no
STT, LLM or TTS, so the numbers measure the platform and nothing else. `BENCH_HEAVY=1` adds a
Silero VAD load and a much bigger image, to show what model weight does to cold starts.

## What gets measured (per run)

| Field | Meaning | Clock |
|---|---|---|
| `join_ms` | trigger -> agent participant joins the room | harness |
| `subscribed_ms` | trigger -> agent audio track subscribed | harness |
| `first_audio_ms` | trigger -> first audible frame from the agent | harness |
| `agent.*` | process start, imports done, job received, connected, published | agent (NTP) |
| `survived` | `--hold` only: still ticking after the hold (scale-in / redeploy test) | harness |

The trigger is whatever starts the agent: an explicit dispatch to a registered worker, a Modal
spawn, an AgentCore invoke, or any CLI command (`gcloud run jobs execute`, `aws ecs run-task`).

## Shapes and platforms

| Platform | Shape | Trigger | Cold how |
|---|---|---|---|
| Local worker (baseline) | registered worker | `dispatch` | n/a |
| LiveKit Cloud, Build plan | registered (Cloud scales it) | `dispatch` | idle until scaled to zero |
| LiveKit Cloud, Ship plan | registered, kept warm | `dispatch` | never cold |
| Modal | one call per container | `modal` | `scaledown_window=2` + gap |
| Modal + memory snapshot | one call per container | `modal` (`BENCH_MODAL_FN=run_call_snap`) | same |
| Cerebrium | registered worker | `dispatch` | `min_replicas = 0` |
| Cloud Run Job | one call per container | `command` | every execution is cold |
| Cloud Run worker pool | registered worker | `dispatch` | n/a (no autoscaling) |
| AgentCore | one call per microVM | `agentcore` | every new session |
| Fargate | registered service / RunTask per call | `dispatch` / `command` | task start |

## Run

```bash
# harness host: any machine near the LiveKit Cloud region
pip install -r harness/requirements.txt          # + modal / boto3 as needed
export LIVEKIT_URL=wss://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=...

python harness/bench.py --platform modal --trigger modal --label cold --runs 30 --gap 30
python harness/bench.py --platform modal --trigger modal --label warm --runs 30 --gap 0
python harness/bench.py --platform fargate --trigger dispatch --label hold --runs 1 --hold 900
python harness/summarize.py results.jsonl
```

## Local check (already passing)

With a local livekit-server and a warm registered worker: join 0.42 s, first audio 0.45 s (p50,
3 runs). One-call-per-process from cold: first audio 0.63-0.86 s, of which about 0.4-0.6 s is
Python imports. With no worker registered and a worker that comes up 3 s after the dispatch,
the job is never served: the server logs `failed to send job request` and the caller waits
forever (livekit-server 1.9.1).

Gotcha found while building this: awaiting `set_attributes` before sending audio delayed the
first audio by 5 s on livekit-server 1.9.1, so the agent sends its timings as a data packet
after the first frame instead.
