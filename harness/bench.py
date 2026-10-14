"""Measure how fast an agent shows up in a room, and whether it survives long calls.

For every run the harness joins a fresh room as the caller, fires a trigger, and records:
  join_ms        trigger -> agent participant joined (harness clock)
  subscribed_ms  trigger -> agent audio track subscribed (harness clock)
  first_audio_ms trigger -> first loud audio frame from the agent (harness clock)
  agent timings  process start / imports / job received / connected (agent clock, NTP)

Hold mode (--hold) keeps the call open and records each 1 s tick from the agent, so a
platform scale-in or redeploy shows up as the moment the ticks stop.

Usage:
  python bench.py --platform modal --trigger modal --runs 30 --gap 0
  python bench.py --platform cloudrun-pool --trigger dispatch --runs 30 --gap 900   # cold
  python bench.py --platform fargate --trigger dispatch --runs 1 --hold 900
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np
from livekit import api, rtc
from triggers import TRIGGERS

LOUD_RMS = 2000  # int16 RMS; the greeting tone is ~11,500, silence is 0


async def one_run(platform: str, trigger_name: str, timeout: float, hold: float) -> dict:
    room_name = f"bench-{platform}-{uuid.uuid4().hex[:8]}"
    async with api.LiveKitAPI() as lk:
        await lk.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=60))
    token = (
        api.AccessToken()
        .with_identity("caller")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )
    room = rtc.Room()
    result: dict = {"platform": platform, "trigger": trigger_name, "room": room_name}
    joined = asyncio.Event()
    heard = asyncio.Event()
    ticks: list[float] = []

    @room.on("participant_connected")
    def _on_join(p: rtc.RemoteParticipant) -> None:
        if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            result["agent_joins"] = result.get("agent_joins", 0) + 1
        if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT and not joined.is_set():
            result["t_join"] = time.time()
            joined.set()

    async def _listen(track: rtc.Track) -> None:
        loud = False
        async for ev in rtc.AudioStream(track, sample_rate=48000, num_channels=1):
            samples = np.frombuffer(ev.frame.data, dtype=np.int16).astype(np.float32)
            is_loud = float(np.sqrt(np.mean(samples**2))) > LOUD_RMS
            now = time.time()
            if is_loud and not heard.is_set():
                result["t_audio"] = now
                heard.set()
            if is_loud and not loud:
                ticks.append(now)
            loud = is_loud

    @room.on("data_received")
    def _on_data(packet: rtc.DataPacket) -> None:
        if packet.topic == "bench.timings":
            result["agent"] = json.loads(packet.data)["timings"]

    @room.on("track_subscribed")
    def _on_track(track: rtc.Track, *_: object) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            result.setdefault("t_subscribed", time.time())
            asyncio.ensure_future(_listen(track))

    await room.connect(os.environ["LIVEKIT_URL"], token)
    try:
        result["t_trigger"] = time.time()
        await TRIGGERS[trigger_name](room_name)
        await asyncio.wait_for(heard.wait(), timeout)
        result["join_ms"] = round((result["t_join"] - result["t_trigger"]) * 1000)
        result["first_audio_ms"] = round((result["t_audio"] - result["t_trigger"]) * 1000)
        result["subscribed_ms"] = round((result["t_subscribed"] - result["t_trigger"]) * 1000)
        for _ in range(25):  # the agent sends its own timings right after its first audio
            if "agent" in result:
                break
            await asyncio.sleep(0.2)
        if hold:
            await asyncio.sleep(hold)
            result["ticks"] = len(ticks)
            result["last_tick_s"] = round(ticks[-1] - result["t_audio"], 1) if ticks else None
            result["survived"] = bool(ticks) and time.time() - ticks[-1] < 3
            # a redeploy that kills the agent and re-dispatches shows up as a long silence
            gaps = [b - a for a, b in zip(ticks, ticks[1:], strict=False)]
            result["max_tick_gap_s"] = round(max(gaps), 1) if gaps else None
    except asyncio.TimeoutError:
        result["error"] = f"no agent audio within {timeout}s"
    except Exception as e:  # recorded, not raised: one bad run shouldn't end the batch
        result["error"] = repr(e)
    finally:
        await room.disconnect()
        # delete the room so the agent session ends now, not after the empty timeout
        async with api.LiveKitAPI() as lk:
            await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
    return result


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, help="label written to the results")
    ap.add_argument("--trigger", required=True, choices=sorted(TRIGGERS))
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--gap", type=float, default=5, help="seconds between runs (long gap = cold)")
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument("--hold", type=float, default=0, help="keep each call open this many seconds")
    ap.add_argument("--label", default="", help="e.g. cold, warm, heavy")
    ap.add_argument("--out", default="results.jsonl")
    args = ap.parse_args()

    out = Path(args.out)
    for i in range(args.runs):
        r = await one_run(args.platform, args.trigger, args.timeout, args.hold)
        r.update(run=i, label=args.label)
        with out.open("a") as f:
            f.write(json.dumps(r) + "\n")
        print(
            f"[{args.platform} {args.label} #{i}] join={r.get('join_ms')}ms "
            f"audio={r.get('first_audio_ms')}ms {r.get('error', '')}",
            flush=True,
        )
        if i < args.runs - 1:
            await asyncio.sleep(args.gap)


if __name__ == "__main__":
    asyncio.run(main())
