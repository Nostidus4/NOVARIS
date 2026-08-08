# Q-SHIELD frontend (Next.js) — Yarn Classic
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Server-side fetch dùng hostname Docker; browser gọi host đã publish
ARG QSHIELD_API_URL=http://backend:8000
ARG NEXT_PUBLIC_QSHIELD_API_URL=http://localhost:8000
ENV QSHIELD_API_URL=$QSHIELD_API_URL \
    NEXT_PUBLIC_QSHIELD_API_URL=$NEXT_PUBLIC_QSHIELD_API_URL

RUN yarn build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder /app/package.json /app/yarn.lock ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/tsconfig.json ./

EXPOSE 3000
CMD ["yarn", "start", "-H", "0.0.0.0", "-p", "3000"]
