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

Before you can run our Ansible playbooks, you need to meet the following
prerequisites:

* Create a DigitalOcean API token, and pass it to the inventory generator by
  setting the `DO_API_TOKEN` environment variable.
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

Provisioning a new server
=========================

Naming
------

We follow a simplified version of the naming scheme on [this blog
post](https://mnx.io/blog/a-proper-server-naming-scheme/):

* Servers are named `<prefix>.matplotlib.org` in A records.
* Servers get a functional CNAME alias (e.g., `web01.matplotlib.org`).
* matplotlib.org is a CNAME to the functional CNAME of a server.

We use [planets in our Solar System](https://namingschemes.com/Solar_System)
for the name prefix. When creating a new server, pick the next one in the list.

Initial setup
-------------

The summary of the initial setup is:

1. Create the droplet with monitoring and relevant SSH keys.
2. Assign new droplet to the matplotlib.org project and the Web firewall.
3. Grab the SSH host fingerprints.
4. Reboot.

We currently use a simple $5 droplet from DigitalOcean. You can create one from
the control panel, or using the `doctl` utility. Be sure to enable monitoring,
and add the `website` tag and relevant SSH keys to the droplet. An example of
using `doctl` is the following:

```
doctl compute droplet create \
    --image fedora-35-x64 \
    --region tor1 \
    --size s-1vcpu-1gb \
    --ssh-keys <key-id>,<key-id> \
    --tag-name website \
    --enable-monitoring \
    venus.matplotlib.org
```

Note, you will have to use `doctl compute ssh-key list` to get the IDs of the
relevant SSH keys saved on DigitalOcean, and substitute them above. Save the ID
of the new droplet from the output, e.g., in:

```
ID           Name       Public IPv4    Private IPv4    Public IPv6    Memory    VCPUs    Disk    Region    Image            VPC UUID    Status    Tags       Features                    Volumes
294098687    mpl.org                                                  1024      1        25      tor1      Fedora 35 x64                new       website    monitoring,droplet_agent
```

the droplet ID is 294098687.


You should also assign the new droplet to the `matplotlib.org` project and the
`Web` firewall:

```
doctl projects list
# Get ID of the matplotlib.org project from the output.
doctl projects resources assign <project-id> --resource=do:droplet:<droplet-id>


doctl compute firewall list
# Get ID of the Web firewall from the output.
doctl compute firewall add-droplets <firewall-id> --droplet-ids <droplet-id>
```

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
1024 SHA256:ExviVyBRoNKsZpgmIfBaejh1ElOpJ/9fC+ki2Fn5Xj4 root@venus.matplotlib.org (DSA)
256 SHA256:hLA7ePr0D4AgiC21IXowtbpcUNnTGgpPB7NOYepQtxg root@venus.matplotlib.org (ECDSA)
256 SHA256:MggFZQbZ7wID1Se2EmOwAm8AaJeA97L8sD8DhSrKy1g root@venus.matplotlib.org (ED25519)
3072 SHA256:MCkDgfbn0sMTCtvAtfD0HmGJV3LVTjpUj6IcfWRHRQo root@venus.matplotlib.org (RSA)
```

Finally, you should reboot the droplet. This is due to a bug in cloud-init on
DigitalOcean, which generates a new machine ID after startup, causing system
logs to be seem invisible.

DNS setup
---------

1. Add an A record for `<prefix>.matplotlib.org` to the IPv4 address of the new
   droplet.
2. Add a CNAME record for `webNN.matplotlib.org` pointing to the given
   `<prefix.matplotlib.org>`.

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
