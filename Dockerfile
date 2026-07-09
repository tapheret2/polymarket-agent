FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md LICENSE requirements.txt ./
COPY src ./src
COPY data/raw/.gitkeep data/raw/
COPY data/processed/.gitkeep data/processed/

RUN pip install --no-cache-dir -e .

# Persist scans/paper outside the container
VOLUME ["/app/data"]

ENTRYPOINT ["pm-agent"]
CMD ["daily-scan", "--limit", "50", "--top", "20"]
