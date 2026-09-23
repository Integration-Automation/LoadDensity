FROM python:3.12-slim

ARG VERSION=0.0.67

RUN pip install --no-cache-dir \
    "je_load_density[all]==${VERSION}" \
    "kopf>=1.37" \
    "kubernetes>=29"

COPY operator.py /opt/operator.py

# The operator only talks to the Kubernetes API; it does not need root inside the container.
RUN useradd --system --uid 10001 --no-create-home operator
USER 10001

ENTRYPOINT ["kopf", "run", "-A", "/opt/operator.py"]
