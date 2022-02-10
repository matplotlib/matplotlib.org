ARG CADDY_VERSION=latest
ARG WEBHOOK_VERSION=latest
FROM docker.io/library/caddy:${CADDY_VERSION}-builder AS builder

RUN xcaddy build \
    --with github.com/WingLim/caddy-webhook@${WEBHOOK_VERSION}

FROM docker.io/library/caddy:${CADDY_VERSION}

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
