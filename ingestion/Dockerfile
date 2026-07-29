FROM python:3.11-slim

WORKDIR /app

# System deps needed by docling (PDF/image processing) and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY ingestion/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion/src ./src
# doc/anmol is bind-mounted at runtime by docker-compose; this default keeps
# `docker run` usable standalone too.
COPY doc/anmol ./doc/anmol

ENTRYPOINT ["python", "-m", "src.main"]
