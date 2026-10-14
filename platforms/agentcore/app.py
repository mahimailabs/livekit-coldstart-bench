"""AWS Bedrock AgentCore Runtime: one microVM session per call, as in AWS's LiveKit sample.

Deploy with the AgentCore starter toolkit from this folder (copy ../../agent/*.py next to it),
using the light or heavy requirements, then set BENCH_AGENTCORE_ARN for the harness.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from oneshot import run_call

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    return run_call(payload["room"])


if __name__ == "__main__":
    app.run()
