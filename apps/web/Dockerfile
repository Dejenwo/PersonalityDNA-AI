# syntax=docker/dockerfile:1
# Build context: repository root (pnpm workspace).
FROM node:22-alpine AS base
RUN corepack enable

FROM base AS build
WORKDIR /repo
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
COPY packages/design-tokens/package.json packages/design-tokens/
COPY packages/configuration/package.json packages/configuration/
RUN pnpm install --frozen-lockfile --filter @pdna/web...
COPY packages packages
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @pdna/web build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN adduser -D -u 10001 pdna
COPY --from=build --chown=pdna /repo/apps/web/.next/standalone ./
COPY --from=build --chown=pdna /repo/apps/web/.next/static ./apps/web/.next/static
USER pdna
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
