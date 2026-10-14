"""Registered-worker shape: `python agent.py start` keeps a worker connected to LiveKit.

Used on LiveKit Cloud, Cerebrium, Cloud Run worker pools, Fargate services and
Azure Container Apps. The harness reaches it with an explicit dispatch to
agent_name "bench".
"""

from __future__ import annotations

import os
import time

from core import process_start_time, run_in_room
from livekit.agents import AgentServer, JobContext, JobProcess, cli

T_IMPORTED = time.time()
HEAVY = os.getenv("BENCH_HEAVY") == "1"

server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    if HEAVY:
        from livekit.plugins import silero

        proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="bench")
async def entrypoint(ctx: JobContext) -> None:
    timings = {
        "process_start": process_start_time(),
        "imported": T_IMPORTED,
        "job_received": time.time(),
    }
    await ctx.connect()
    await run_in_room(ctx.room, timings)
    # end the session as soon as the caller leaves; otherwise it lingers until the room
    # closes (~30 s on LiveKit Cloud) and counts against the plan's concurrency limit
    ctx.shutdown(reason="caller left")


if __name__ == "__main__":
    cli.run_app(server)
