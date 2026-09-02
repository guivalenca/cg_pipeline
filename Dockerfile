FROM node:24-bookworm-slim AS node-runtime

WORKDIR /opt/cg-pipeline
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ffmpeg poppler-utils yt-dlp \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

WORKDIR /app
COPY . .
COPY --from=node-runtime /opt/cg-pipeline/node_modules ./node_modules
RUN python -m pip install --no-cache-dir .

CMD ["uvicorn", "universe.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
