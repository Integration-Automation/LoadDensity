ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim
COPY dist/*.whl /wheels/
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked python -m pip install --only-binary :all: /wheels/*.whl
ARG EXTRA=base
RUN if [ "$EXTRA" = "gui" ] || [ "$EXTRA" = "all" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        libegl1 libgl1 libopengl0 libglib2.0-0 libxkbcommon0 libdbus-1-3 libfontconfig1 \
        libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0 \
        libxcb-randr0 libxcb-render-util0 libxcb-image0 fonts-dejavu-core \
      && rm -rf /var/lib/apt/lists/*; \
    fi
COPY test/smoke /checks/smoke
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked python /checks/smoke/install_extra.py "$EXTRA"
ENV LD_EXTRA=${EXTRA} QT_QPA_PLATFORM=offscreen AWS_EC2_METADATA_DISABLED=true
USER 65534:65534
WORKDIR /tmp
CMD ["python", "/checks/smoke/run_cell.py"]
