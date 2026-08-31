FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --system saleswiki \
    && useradd --system --gid saleswiki --home-dir /app --shell /usr/sbin/nologin saleswiki \
    && mkdir -p /runtime \
    && chown -R saleswiki:saleswiki /app /runtime

USER saleswiki

CMD ["python", "scripts/demo_dryrun.py", "--quiet"]
