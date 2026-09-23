FROM python:3.12-slim

# The operator only needs kopf and the Kubernetes client: the load itself runs in pods started from the
# LoadDensity image. Dependencies come from a hash-locked, wheels-only requirements file, regenerated with
#   uv pip compile requirements.in --generate-hashes --python-version 3.12 \
#       --python-platform x86_64-manylinux_2_28 --only-binary :all: -o requirements.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY operator.py /opt/operator.py

# The operator only talks to the Kubernetes API; it does not need root inside the container.
RUN useradd --system --uid 10001 --no-create-home loaddensity
USER 10001

ENTRYPOINT ["kopf", "run", "-A", "/opt/operator.py"]
