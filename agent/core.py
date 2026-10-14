"""Shared benchmark agent body: join a room, beep once, then tick every second.

The same code runs in both deployment shapes:
- registered worker (agent.py): LiveKit dispatches a job to an always-on worker
- one call per container (oneshot.py): the platform starts a process for one room

No STT/LLM/TTS is involved, so the numbers measure the platform, not model APIs.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import time

from livekit import rtc

SAMPLE_RATE = 48000
FRAME_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000


def process_start_time() -> float:
    """Wall-clock time this process was started (Linux), else now."""
    try:
        with open("/proc/self/stat") as f:
            start_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat") as f:
            btime = next(int(line.split()[1]) for line in f if line.startswith("btime"))
        return btime + start_ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, StopIteration):
        return time.time()


def _tone(ms: int, freq: float, amp: float) -> list[rtc.AudioFrame]:
    frames = []
    n_frames = ms // FRAME_MS
    for i in range(n_frames):
        frame = rtc.AudioFrame.create(SAMPLE_RATE, 1, SAMPLES_PER_FRAME)
        data = frame.data
        for j in range(SAMPLES_PER_FRAME):
            t = (i * SAMPLES_PER_FRAME + j) / SAMPLE_RATE
            data[j] = int(amp * 32767 * math.sin(2 * math.pi * freq * t))
        frames.append(frame)
    return frames


GREETING = _tone(1000, 440.0, 0.5)
TICK = _tone(100, 880.0, 0.3)
SILENCE = rtc.AudioFrame.create(SAMPLE_RATE, 1, SAMPLES_PER_FRAME)


async def run_in_room(room: rtc.Room, timings: dict[str, float], max_call_s: float = 3600) -> None:
    """Publish audio into an already-connected room until every caller has left."""
    timings["connected"] = time.time()
    source = rtc.AudioSource(SAMPLE_RATE, 1)
    track = rtc.LocalAudioTrack.create_audio_track("bench", source)
    await room.local_participant.publish_track(
        track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    )
    timings["published"] = time.time()
    payload = json.dumps({"timings": timings, "platform": os.getenv("BENCH_PLATFORM", "")})

    def callers() -> int:
        return sum(
            1
            for p in room.remote_participants.values()
            if p.kind != rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
        )

    for i, frame in enumerate(GREETING):
        await source.capture_frame(frame)
        if i == 0:
            # timings go out as a data packet once audio is flowing, so they never delay it
            await room.local_participant.publish_data(payload, reliable=True, topic="bench.timings")

    deadline = time.monotonic() + max_call_s
    # one 100 ms tick per second, so the harness can see exactly when the agent dies
    while time.monotonic() < deadline:
        for frame in TICK:
            await source.capture_frame(frame)
        for _ in range((1000 - 100) // FRAME_MS):
            await source.capture_frame(SILENCE)
        if callers() == 0:
            await asyncio.sleep(2)
            if callers() == 0:
                break
