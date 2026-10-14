"""Ways to get an agent into a room. Each trigger starts the agent for one room and returns.

Platform SDKs are imported lazily so the harness runs with only the ones you use installed.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from collections.abc import Awaitable, Callable

from livekit import api

Trigger = Callable[[str], Awaitable[None]]


async def dispatch(room: str) -> None:
    """Explicit dispatch to a registered worker (LiveKit Cloud, Cerebrium, worker pools...)."""
    async with api.LiveKitAPI() as lk:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=os.getenv("BENCH_AGENT_NAME", "bench"), room=room
            )
        )


async def modal_spawn(room: str) -> None:
    import modal

    fn = modal.Function.from_name(
        os.getenv("BENCH_MODAL_APP", "lk-bench"), os.getenv("BENCH_MODAL_FN", "run_call")
    )
    await fn.spawn.aio(room)


async def agentcore_invoke(room: str) -> None:
    import json

    import boto3

    client = boto3.client("bedrock-agentcore", region_name=os.getenv("AWS_REGION", "us-east-1"))

    def _invoke() -> None:
        # returns only when the session ends, so fire it on a thread and move on
        client.invoke_agent_runtime(
            agentRuntimeArn=os.environ["BENCH_AGENTCORE_ARN"],
            runtimeSessionId=f"{room}-{'x' * max(0, 33 - len(room))}",
            payload=json.dumps({"room": room}).encode(),
        )

    asyncio.get_running_loop().run_in_executor(None, _invoke)


async def command(room: str) -> None:
    """Run any CLI with {room} filled in, e.g.

    BENCH_COMMAND='gcloud run jobs execute lk-bench --async --update-env-vars BENCH_ROOM={room}'
    """
    cmd = os.environ["BENCH_COMMAND"].format(room=shlex.quote(room))
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.DEVNULL)
    if await proc.wait() != 0:
        raise RuntimeError(f"trigger command failed: {cmd}")


TRIGGERS: dict[str, Trigger] = {
    "dispatch": dispatch,
    "modal": modal_spawn,
    "agentcore": agentcore_invoke,
    "command": command,
}
