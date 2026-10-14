"""Modal: one function call per phone call.

  modal secret create livekit-bench LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=...
  modal deploy platforms/modal_app.py
  BENCH_MODAL_APP=lk-bench python harness/bench.py --platform modal --trigger modal ...

Four functions so one deploy covers light/heavy with and without memory snapshots.
The harness picks one with BENCH_MODAL_FN (default run_call).
"""

from __future__ import annotations

import os
from pathlib import Path

import modal

AGENT_DIR = Path(__file__).parent.parent / "agent"
app = modal.App("lk-bench")
secret = modal.Secret.from_name("livekit-bench")

light = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(AGENT_DIR / "requirements.txt"))
    .env({"BENCH_PLATFORM": "modal"})
    .add_local_dir(AGENT_DIR, "/agent")
)
heavy = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(AGENT_DIR / "requirements-heavy.txt"))
    .env({"BENCH_PLATFORM": "modal", "BENCH_HEAVY": "1"})
    .add_local_dir(AGENT_DIR, "/agent", copy=True)
    .run_commands("cd /agent && python agent.py download-files")
)

# scaledown_window=2 makes every call after an idle gap a true cold start;
# the harness sets the gap between runs
common = dict(secrets=[secret], timeout=3600, scaledown_window=2, cpu=1.0, memory=2048)


if not modal.is_local():
    # import at module level inside the container, so memory snapshots capture
    # the imports (and the heavy model load) instead of redoing them per call
    import sys

    sys.path.insert(0, "/agent")
    os.chdir("/agent")
    from oneshot import run_call as _run_call


def _run(room: str) -> dict:
    return _run_call(room)


@app.function(image=light, **common)
def run_call(room: str) -> dict:
    return _run(room)


@app.function(image=light, enable_memory_snapshot=True, **common)
def run_call_snap(room: str) -> dict:
    return _run(room)


@app.function(image=heavy, **common)
def run_call_heavy(room: str) -> dict:
    return _run(room)


@app.function(image=heavy, enable_memory_snapshot=True, **common)
def run_call_heavy_snap(room: str) -> dict:
    return _run(room)
