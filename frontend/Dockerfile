FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm && pnpm build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system rapp && adduser --system --ingroup rapp rapp

COPY --from=builder /app/public ./public
COPY --from=builder --chown=rapp:rapp /app/.next/standalone ./
COPY --from=builder --chown=rapp:rapp /app/.next/static ./.next/static

USER rapp
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
