ARG CADDY_VERSION=latest
ARG CADDY_GIT_VERSION=latest
FROM docker.io/library/caddy:${CADDY_VERSION}-builder AS builder

RUN xcaddy build \
    --with github.com/greenpau/caddy-git@${CADDY_GIT_VERSION}

FROM docker.io/library/caddy:${CADDY_VERSION}

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
