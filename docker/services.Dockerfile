FROM python:3.12-slim
COPY dist/*.whl /wheels/
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    for wheel in /wheels/*.whl; do python -m pip install --only-binary :all: "$wheel[redis,mqtt,sql]"; done && \
    python -m pip check
COPY test/smoke /checks/smoke
USER 65534:65534
WORKDIR /tmp
CMD ["python", "/checks/smoke/service_probe.py"]
