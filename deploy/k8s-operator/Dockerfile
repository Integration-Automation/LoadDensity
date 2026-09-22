FROM python:3.12-slim

ARG VERSION=0.0.67

RUN pip install --no-cache-dir \
    "je_load_density[all]==${VERSION}" \
    "kopf>=1.37" \
    "kubernetes>=29"

COPY operator.py /opt/operator.py

ENTRYPOINT ["kopf", "run", "-A", "/opt/operator.py"]
