# Roadmap

Rounds 1 and 2 covered six platforms: LiveKit Cloud, Cerebrium, Modal, Google Cloud Run, AWS Bedrock AgentCore and AWS Fargate. This is what's next. Pick one and see [CONTRIBUTING.md](CONTRIBUTING.md).

## More platforms

| Platform | Shape to test | Why it's interesting |
| --- | --- | --- |
| Azure Container Apps | worker (min replicas 1) and job per call | scale-to-zero with KEDA, a drain window you can configure |
| Fly.io Machines | worker, plus a machine started per call | fast machine starts are the pitch; measure them |
| Railway | worker | always-on and simple, a common hobby default |
| Render | background worker | same, plus a deploy-time drain setting |
| Koyeb | worker with scale-to-zero | the cold path fires on a request; does a dispatch ever reach it? |
| RunPod serverless (CPU) | one call per job | GPU-first platform, cold start on CPU workers |
| Beam | one call per function | Modal-like, with its own snapshot story |
| Baseten | one call per invocation | built for model serving, not long calls |
| Cloudflare Containers | one call per container | new; the cold start is the open question |
| Google Kubernetes Engine Autopilot | worker deployment | the self-managed baseline most teams end up on |
| A plain VM (Hetzner or EC2) | worker under systemd | the floor without any platform in the way |

## Better measurements

- **A real agent.** Add STT, an LLM and TTS (imports, model downloads, first token) next to the tone agent. Cold starts get worse when there are real imports.
- **Bigger samples.** At least 50 runs per row and p99, over several days. The current rows are 10 to 21 runs.
- **More regions.** Run the harness from Europe and Asia against platforms in the same region.
- **Concurrency bursts.** Start 10 and then 50 calls at once: who queues, who scales, who drops?
- **Drain fixes.** Rerun the redeploy test with ECS `stopTimeout` at 120 s, Cloud Run's longest grace period and LiveKit's drain timeout. Does any setting keep a 10-minute call alive?
- **LiveKit Cloud cold.** Get a cold number on a plan or deployment that actually scales to zero.
- **Per-track tick logging.** Confirm whether two agents overlap after a Cloud Run redeploy.
- **Trigger overhead.** Subtract the `gcloud` and boto3 client time so platform time stands alone.

## Repo hygiene

- Check in the deploy scripts for Cloud Run (job and worker pool) and Fargate under `platforms/`. Today they're only described in `results/NOTES.md`.
- A teardown script per platform.
- CI that runs ruff and checks that `summarize.py` works on every file in `results/`.
