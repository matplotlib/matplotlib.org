#!/usr/bin/env python3
"""
GitHub Documentation WebHook handler.

This web server handles webhooks from GitHub in order to trigger an update of
git checkouts. The git checkouts exist in the site directory pointed to by the
`SITE_DIR` environment variable (defaults to `sites`).

The repository is required to be in the `matplotlib` organization, and will be
found as a subdirectory of the site directory.

The secret for each repository is defined in the `WEBHOOK_{repo}_SECRET`
environment variable, where `{repo}` is the name of the repository with special
characters replaced by underscore and converted to upper case.
"""

import asyncio
import hmac
import json
import logging
import os
from pathlib import Path
import sys

from aiohttp import web


log = logging.getLogger('webhook')
logging.basicConfig(level=logging.DEBUG)


async def update_repo(repo: Path, delivery: str, name: str):
    """Update a git repo at the given path."""
    if not (repo / '.git').is_dir():
        raise web.HTTPServerError(
            reason=f'{delivery}: Checkout for {name} does not exist')

    proc = await asyncio.create_subprocess_exec('git', 'pull', cwd=repo)
    try:
        await asyncio.wait_for(proc.wait(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        raise web.HTTPServerError(
            reason=f'{delivery}: Timed out updating git checkout of {name}')


async def verify_signature(data: bytes, signature: bytes, repo: str,
                           delivery: str):
    """
    Verify data matches signature from GitHub.

    https://docs.github.com/en/developers/webhooks-and-events/webhooks/securing-your-webhooks
    """
    envvar = repo.replace('.', '_').replace('-', '_').upper()
    secret = os.environb.get(f'WEBHOOK_{envvar}_SECRET'.encode('utf-8'))
    if secret is None:
        raise web.HTTPBadRequest(
            reason=f'{delivery}: Secret for {repo} was not set')
    digest = hmac.new(secret, data, 'sha256').hexdigest()

    if not hmac.compare_digest(signature, f'sha256={digest}'):
        raise web.HTTPBadRequest(
            reason=f'{delivery}: webhook signature was invalid')


async def github_webhook(request: web.Request):
    """
    Handle webhooks from GitHub.

    We only handle ping and push events (this is enforced by the Caddyfile).
    """
    # Verify some input parameters.
    if request.content_length > 25_000_000:  # Limit from GitHub.
        raise web.HTTPBadRequest(reason='Request too large')

    # This should be guarded against by Caddy, but check anyway.
    # https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#delivery-headers
    try:
        delivery = request.headers['X-GitHub-Delivery']
    except KeyError:
        raise web.HTTPBadRequest(reason='No delivery given')
    try:
        signature = request.headers['X-Hub-Signature-256']
    except KeyError:
        raise web.HTTPBadRequest(reason='No signature given')
    try:
        event = request.headers['X-GitHub-Event']
    except KeyError:
        raise web.HTTPBadRequest(reason='No event given')
    repo = request.match_info.get('repo')
    log.info('%s: Received webhook for %s', delivery, repo)

    data = await request.read()
    await verify_signature(data, signature, repo, delivery)

    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(reason='Invalid data input')

    # https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#webhook-payload-object-common-properties
    try:
        sender = data['sender']['login']
        repository = data['repository']
    except (KeyError, TypeError):
        raise web.HTTPBadRequest(reason='Missing required fields')
    try:
        organization = repository['owner']['login']
        repository = repository['name']
    except KeyError:
        raise web.HTTPBadRequest(reason='Missing required fields')
    log.info('%s: Received %s event from %s on %s/%s',
             delivery, event, sender, organization, repository)

    if organization != 'matplotlib':
        raise web.HTTPBadRequest(reason=f'{delivery}: incorrect organization')
    if repository != repo:
        raise web.HTTPBadRequest(reason=f'{delivery}: incorrect repository')

    if event == 'ping':
        log.info('%s: Ping %s: %s', delivery, data['hook_id'], data['zen'])
        return web.Response(status=200)

    if event != 'push':
        log.info('%s: Ignoring webhook for unused event %s', delivery, event)
        return web.Response(status=200)

    checkout = Path(os.environ.get('SITE_DIR', 'sites'), repository)
    await update_repo(checkout, delivery, f'{organization}/{repository}')

    return web.Response(status=200)


def create_app():
    """Create the aiohttp app and setup routes."""
    app = web.Application()
    app.add_routes([
        web.post('/gh/{repo}', github_webhook),
    ])
    return app


if __name__ == '__main__':
    assert Path(os.environ.get('SITE_DIR', 'sites')).is_dir()

    if len(sys.argv) > 1:
        from urllib.parse import urlparse
        url = sys.argv[1]
        if not url.startswith('http://'):
            url = f'http://{url}'
        url = urlparse(url)
        host = url.hostname
        port = url.port
    else:
        host = 'localhost'
        port = 8080
    app = create_app()
    web.run_app(app, host=host, port=port)
