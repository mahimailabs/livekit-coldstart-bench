# AgentCore Runtime needs an ARM64 image serving /ping and /invocations on port 8080.
#   docker buildx build --platform linux/arm64 -f platforms/agentcore/Dockerfile -t lk-bench:agentcore .
ARG BASE=python:3.12-slim
FROM ${BASE}
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 BENCH_PLATFORM=agentcore
WORKDIR /app
COPY agent/requirements.txt ./
RUN pip install --no-cache-dir uv==0.9.5 && \
    uv pip install --system -r requirements.txt bedrock-agentcore==1.24.1
COPY agent/ ./
COPY platforms/agentcore/app.py ./
EXPOSE 8080
CMD ["python", "app.py"]
