# One image for every container platform. Build twice:
#   docker build -f platforms/Dockerfile -t lk-bench:light .
#   docker build -f platforms/Dockerfile --build-arg HEAVY=1 -t lk-bench:heavy .
# CMD runs a registered worker; per-call platforms override it with
#   python oneshot.py   (reads BENCH_ROOM)
ARG BASE=python:3.12-slim
FROM ${BASE}
ARG HEAVY=0
ENV BENCH_HEAVY=${HEAVY} UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY agent/requirements.txt agent/requirements-heavy.txt ./
RUN pip install --no-cache-dir uv==0.9.5 && \
    if [ "$HEAVY" = "1" ]; then uv pip install --system -r requirements-heavy.txt; \
    else uv pip install --system -r requirements.txt; fi
COPY agent/ ./
# bake model files into the image so a cold start never downloads them
RUN if [ "$HEAVY" = "1" ]; then python agent.py download-files; fi
EXPOSE 8081
CMD ["python", "agent.py", "start"]
