matplotlib.org Hosting
======================

This repo enables matplotlib.org hosting using
[Caddy](https://caddyserver.com/).

By default, Caddy is run in a container using `make serve`, which:

* Runs Caddy (version can be overridden by setting `CADDY_VERSION`) in
  [podman](https://podman.io/) (can be switched to docker by setting `RUNTIME`)
* Mounts Matplotlib documentation repositories from the  `sites` subdirectory
* Exposes the server on port 2015

Hosted repositories
-------------------

At the top level, Caddy exposes the `mpl-brochure-site` repository with
fallback to files in the `matplotlib.github.com` repository. The following
related projects are also exposed as toplevel directories:

* [basemap](https://github.com/matplotlib/basemap)
* [cheatsheets](https://github.com/matplotlib/cheatsheets)
* [governance](https://github.com/matplotlib/governance)
* [matplotblog](https://github.com/matplotlib/matplotblog)
* [mpl-altair](https://github.com/matplotlib/mpl-altair)
* [mpl-bench](https://github.com/matplotlib/mpl-bench)
* [mpl-third-party](https://github.com/matplotlib/mpl-third-party)

Caddy options
-------------

The Makefile will set these options for you when mounting and running the
container, but if you wish to run Caddy directly, you may wish to set some
overrides in environment variables:

* The host and port with `SITE_ADDRESS` (defaults to port 2015 on all
  interfaces)
* The directory containing the git repositories with `SITE_DIR` (defaults to
  `sites` in the current directory)
