RUNTIME ?= podman
CADDY_IMAGE ?= caddy-mpl
CADDY_VERSION ?= 2.4.6
CADDY_GIT_VERSION ?= 1.0.4

serve:
	mkdir -p sites
	$(RUNTIME) run --rm -it \
	    -v $$PWD/sites:/srv:Z \
	    -v $$PWD/Caddyfile:/etc/caddy/Caddyfile:ro,Z \
	    -e SITE_DIR=/srv \
	    -p 2015:2015 \
	    $(CADDY_IMAGE):$(CADDY_VERSION) \
	    caddy run --config /etc/caddy/Caddyfile --watch

image:
	$(RUNTIME) build \
	    --build-arg=CADDY_VERSION=$(CADDY_VERSION) \
	    --build-arg=CADDY_GIT_VERSION=v$(CADDY_GIT_VERSION) \
	    -t $(CADDY_IMAGE):$(CADDY_VERSION) \
	    -f Containerfile

fmt:
	$(RUNTIME) run --rm -it \
	    -v $$PWD/Caddyfile:/etc/caddy/Caddyfile:Z \
	    $(CADDY_IMAGE):$(CADDY_VERSION) \
	    caddy fmt --overwrite /etc/caddy/Caddyfile
