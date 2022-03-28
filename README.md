matplotlib.org Hosting
======================

This repo enables matplotlib.org hosting using
[Caddy](https://caddyserver.com/).

Hosted repositories
-------------------

At the top level, Caddy exposes the `mpl-brochure-site` repository with
fallback to files in the `matplotlib.github.com` repository. The following
related projects are also exposed as toplevel directories:

* [basemap](https://github.com/matplotlib/basemap)
* [cheatsheets](https://github.com/matplotlib/cheatsheets)
* [cycler](https://github.com/matplotlib/cycler)
* [devdocs](https://github.com/matplotlib/devdocs)
* [governance](https://github.com/matplotlib/governance)
* [matplotblog](https://github.com/matplotlib/matplotblog)
* [mpl-altair](https://github.com/matplotlib/mpl-altair)
* [mpl-bench](https://github.com/matplotlib/mpl-bench)
* [mpl-gui](https://github.com/matplotlib/mpl-gui)
* [mpl-third-party](https://github.com/matplotlib/mpl-third-party)

Ansible configuration
=====================

When running on DigitalOcean hosting, an Ansible playbook is used to configure
the server with consistent settings.

Setup
-----

Before you can run our ansible playbooks, you need to meet the following
prerequisites:

* Create a DigitalOcean API token, and pass it to the inventory generator by
  setting the `DO_API_TOKEN` environment variable.
* Set the vault decryption password of the ansible vaulted file with our
  secrets. This may be done by setting the `ANSIBLE_VAULT_PASSWORD_FILE`
  environment variable to point to a file containing the password.
* Download all the collections the playbooks depend on with the following
  command:
  ```
  ansible-galaxy collection install \
    --requirements-file collections/requirements.yml
  ```

You may wish to use [direnv](https://direnv.net/) to set environment variables.

Running
-------

There is currently only one playbook:

* `matplotlib.org.yml`, for the main matplotlib.org hosting. This playbook
  operates on droplets with the `website` tag in DigitalOcean.
