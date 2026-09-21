# syntax=docker/dockerfile:1.4
# ==============================================================================
# Production Dockerfile: Next.js Admin & Organization Portal (PR-20)
# Multi-stage, standalone, non-root container
# ==============================================================================

FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Stage 1: Dependencies
FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY packages/contracts/package.json ./packages/contracts/
COPY apps/admin/package.json ./apps/admin/
RUN pnpm install --frozen-lockfile --filter admin...

# Stage 2: Builder
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/contracts/node_modules ./packages/contracts/node_modules
COPY --from=deps /app/apps/admin/node_modules ./apps/admin/node_modules
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY packages/contracts ./packages/contracts
COPY apps/admin ./apps/admin

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

RUN pnpm --filter @multilingual/contracts build || true
RUN pnpm --filter admin build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3001 \
    HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 10001 nodejs && \
    adduser --system --uid 10001 nextjs

COPY --from=builder /app/apps/admin/public ./apps/admin/public
COPY --from=builder --chown=nextjs:nodejs /app/apps/admin/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/admin/.next/static ./apps/admin/.next/static

USER nextjs

EXPOSE 3001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3001/ || exit 1

CMD ["node", "apps/admin/server.js"]
