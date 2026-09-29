# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /research
COPY requirements.txt /tmp/requirements.txt
# Optional: behind a TLS-intercepting proxy, build with
#   --secret id=extra_ca,src=/path/to/ca-bundle.crt   (never baked into the image)
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install --no-cache-dir -r /tmp/requirements.txt
# Source is bind-mounted at runtime (see docker-compose.yml).
