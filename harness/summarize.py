"""Turn results.jsonl into a markdown table of p50/p90 per platform and label."""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")]
groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
for r in rows:
    groups[(r["platform"], r.get("label", ""))].append(r)

print(
    "| Platform | Label | Runs | Failed | Join p50 | Join p90 | First audio p50 | First audio p90 |"
)
print("|---|---|---|---|---|---|---|---|")
for (platform, label), rs in sorted(groups.items()):
    ok = [r for r in rs if "first_audio_ms" in r]
    j = [r["join_ms"] for r in ok]
    a = [r["first_audio_ms"] for r in ok]

    def p(xs: list[int], q: int) -> str:
        return f"{np.percentile(xs, q) / 1000:.2f} s" if xs else "-"

    print(
        f"| {platform} | {label} | {len(rs)} | {len(rs) - len(ok)} | "
        f"{p(j, 50)} | {p(j, 90)} | {p(a, 50)} | {p(a, 90)} |"
    )
