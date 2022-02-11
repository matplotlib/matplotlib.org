ARG CADDY_VERSION=latest
FROM docker.io/library/caddy:${CADDY_VERSION}-builder AS builder

RUN xcaddy build

FROM docker.io/library/caddy:${CADDY_VERSION}

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
