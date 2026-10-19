FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends procps ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY policy.mjs limited-stream.mjs crawl.mjs worker.mjs mcp.mjs ./
RUN mkdir -p /data && chown node:node /data
USER node
ENV NODE_ENV=production CRAWLEE_DATA=/data
CMD ["node","worker.mjs"]
COPY --chown=node:node test ./test
