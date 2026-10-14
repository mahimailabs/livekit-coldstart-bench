"""One-call-per-container shape: start, join one room, run the call, exit.

Bypasses LiveKit dispatch entirely, the way AWS's AgentCore LiveKit sample does.
The platform wrapper calls `run_call(room)`; `python oneshot.py --room X` runs it directly.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time

T_START_IMPORT = time.time()

from core import process_start_time, run_in_room  # noqa: E402
from livekit import api, rtc  # noqa: E402

if os.getenv("BENCH_HEAVY") == "1":
    from livekit.plugins import silero

    _VAD = silero.VAD.load()

T_IMPORTED = time.time()


async def _run(room_name: str) -> dict[str, float]:
    timings = {
        "process_start": process_start_time(),
        "import_start": T_START_IMPORT,
        "imported": T_IMPORTED,
        "job_received": time.time(),
    }
    token = (
        api.AccessToken()
        .with_identity(f"agent-{room_name}")
        .with_kind("agent")
        .with_grants(api.VideoGrants(room_join=True, room=room_name, agent=True))
        .to_jwt()
    )
    room = rtc.Room()
    await room.connect(os.environ["LIVEKIT_URL"], token)
    try:
        await run_in_room(room, timings)
    finally:
        await room.disconnect()
    return timings


def run_call(room_name: str) -> dict[str, float]:
    return asyncio.run(_run(room_name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", default=os.getenv("BENCH_ROOM"))
    args = parser.parse_args()
    if not args.room:
        parser.error("--room or BENCH_ROOM is required")
    run_call(args.room)
