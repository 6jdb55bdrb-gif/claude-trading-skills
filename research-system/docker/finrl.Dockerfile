# syntax=docker/dockerfile:1
# FinRL research image (CPU). Heavy: torch + stable-baselines3.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /research
COPY requirements-finrl.lock requirements-finrl.txt /tmp/
# Optional: behind a TLS-intercepting proxy, build with
#   --secret id=extra_ca,src=/path/to/ca-bundle.crt   (never baked into the image)
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then \
      export PIP_CERT=/run/secrets/extra_ca GIT_SSL_CAINFO=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --no-deps -r /tmp/requirements-finrl.lock pytest iniconfig pluggy \
    && pip install --no-cache-dir --no-deps -r /tmp/requirements-finrl.txt
# Source is bind-mounted at runtime (see docker-compose.yml).
