ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim
COPY dist/*.whl /wheels/
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked python -m pip install --only-binary :all: /wheels/*.whl
ARG EXTRA=base
RUN if [ "$EXTRA" = "gui" ] || [ "$EXTRA" = "all" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core libdbus-1-3 libegl1 libfontconfig1 libgl1 libglib2.0-0 libopengl0 \
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
        libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxkbcommon0 \
      && rm -rf /var/lib/apt/lists/*; \
    fi
COPY test/smoke /checks/smoke
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked python /checks/smoke/install_extra.py "$EXTRA"
ENV LD_EXTRA=${EXTRA} QT_QPA_PLATFORM=offscreen AWS_EC2_METADATA_DISABLED=true
RUN useradd --create-home --uid 10001 --user-group --shell /usr/sbin/nologin ld-smoke
USER 10001:10001
WORKDIR /tmp
CMD ["python", "/checks/smoke/run_cell.py"]
