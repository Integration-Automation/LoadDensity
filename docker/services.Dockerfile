FROM python:3.12-slim
COPY dist/*.whl /wheels/
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    for wheel in /wheels/*.whl; do python -m pip install "$wheel[redis,mqtt,sql]"; done && python -m pip check
COPY test/smoke /checks/smoke
WORKDIR /run
CMD ["python", "/checks/smoke/service_probe.py"]
