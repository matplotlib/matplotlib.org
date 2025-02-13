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
* [mpl-sphinx-theme](https://github.com/matplotlib/mpl-sphinx-theme)
* [mpl-third-party](https://github.com/matplotlib/mpl-third-party)
* [data-prototype](https://github.com/matplotlib/data-prototype)

Ansible configuration
=====================

When running on DigitalOcean hosting, an Ansible playbook is used to configure
the server with consistent settings.

Setup
-----

Before you can run our Ansible playbooks, you need to meet the following
prerequisites:

* Create a DigitalOcean API token, and pass it to the inventory generator by
  setting the `DO_API_TOKEN` environment variable.
* If you are creating a new droplet, and want to configure DNS as well, then
  create a CloudFlare API token, and pass it to the Ansible playbook by setting
  the `CLOUDFLARE_TOKEN` environment variable.
* Set the vault decryption password of the Ansible vaulted file with our
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

Adding a new subproject
=======================

When a new repository is added to the Matplotlib organization with
documentation (or an existing repository adds documentation), it will be
necessary to re-configure the server to serve those files. Note, it is
currently assumed that the documentation is on the `gh-pages` branch of the
repository, and it will be served from the top-level subdirectory with the same
name as the repository (similar to GitHub Pages.) There are 4 steps to achieve
this:

1. Generate a secret to secure the webhook. You can follow [GitHub's
   instructions for creating
   one](https://docs.github.com/en/developers/webhooks-and-events/webhooks/securing-your-webhooks).
2. Add repository to Ansible:

   1. Add an entry to the `repos` variable at the top of `matplotlib.org.yml`.
   2. Add the webhook secret to `files/webhook_vars.yml`.

3. Re-run Ansible on the playbook like [below](#running-ansible). This should
   clone the new repository and update the webhook handler.
4. Configure a webhook on the new repository with the following settings:

   - Payload URL of `https://do.matplotlib.org/gh/<repository>`
   - Content type of application/json
   - Use the secret generated in step 1
   - Trigger only on "push" events

If everything is done correctly, the GitHub webhook should have posted an
initial "ping" event successfully, and documentation should be available at
`https://matplotlib.org/<repository>`.

Provisioning a new server
=========================

Naming
------

We follow a simplified version of the naming scheme on [this blog
post](https://mnx.io/blog/a-proper-server-naming-scheme/):

* Servers are named `<prefix>.matplotlib.org` in A records, pointing to the
  IPv4 address of the droplet.
* Servers get a functional CNAME alias (e.g., `web01.matplotlib.org`) pointing
  to the hostname `<prefix>.matplotlib.org`.
* matplotlib.org is a CNAME alias of the functional CNAME of a server.

We use [planets in our Solar System](https://namingschemes.com/Solar_System)
for the name prefix. When creating a new server, pick the next one in the list.

Initial setup
-------------

The summary of the initial setup is:

1. Create the droplet with monitoring and relevant SSH keys.
2. Assign new droplet to the matplotlib.org project.
3. Add DNS entries pointing to the server on CloudFlare.
4. Grab the SSH host fingerprints.
5. Reboot.

We currently use a simple $12 droplet from DigitalOcean. You can create one
from the control panel, or using the `create.yml` Ansible playbook:

```
ansible-playbook create.yml
```

This playbook will prompt you for 3 settings:

1. The host name of the droplet, which should follow the naming convention
   above.
2. The functional CNAME alias of the droplet.
3. The names of SSH keys to add to the droplet.

You may also pass these directly to Ansible as:

```
ansible-playbook create.yml --extra-vars "host=pluto functional=web99 ssh_keys='a b c'"
```

The playbook will create the server, as well as add DNS records on CloudFlare.
Note, you must set `DO_API_TOKEN` and `CLOUDFLARE_TOKEN` in the environment to
access these services.

Then, to ensure you are connecting to the expected server, you should grab the
SSH host keys via the DigitalOcean Droplet Console:

```
for f in /etc/ssh/ssh_host_*_key; do
  ssh-keygen -l -f $f;
done
```

Note down the outputs to verify later, e.g.,

```
# Use these for comparison when connecting yourself.
1024 SHA256:J2sbqvhI/VszBtVvPabgxyz6sRnGLrZUn0kqfv4doAM root@mercury.matplotlib.org (DSA)
256 SHA256:J0rOMayXhL1+5wbm4WQNpAvmscDjqwJjAtk1SLemRMI root@mercury.matplotlib.org (ECDSA)
256 SHA256:y8EDRGMpLWOW72x47MVKsAfSAl8JHjsOc/RGaiMTPGs root@mercury.matplotlib.org (ED25519)
3072 SHA256:AyuNO8FES5k9vobv0Pu9XpvtjVFZ1bTTNxb1lo+AuRA root@mercury.matplotlib.org (RSA)
```

Finally, you should reboot the droplet. This is due to a bug in cloud-init on
DigitalOcean, which generates a new machine ID after startup, causing system
logs to be seem invisible.

Running Ansible
---------------

You must setup Ansible as described above. Verify that the new droplet is
visible to Ansible by running:

```
ansible-inventory --graph
```

which should list the new droplet in the `website` tag:

```
@all:
  |--@website:
  |  |--venus.matplotlib.org
```

Then execute the Ansible playbook on the servers by running:

```
ansible-playbook --user root matplotlib.org.yml
```

During the initial "Gathering Facts" task, you will be prompted to accept the
server's SSH fingerprint, which you should verify against the values found
earlier. If there are existing servers that you don't want to touch, then you
can use the `--limit` option. If you are using a non-default SSH key, you may
wish to use the `--private-key` option.

Flip main DNS
-------------

You can verify that the server is running correctly by connecting to
`https://<prefix>.matplotlib.org` in your browser.

Once everything is running, you should flip the DNS for the main site, changing
the `matplotlib.org` CNAME to point to the new server's `webNN.matplotlib.org`
functional name.
