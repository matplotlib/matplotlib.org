"""GitHub Documentation WebHook handler tests."""

import functools
import subprocess
from unittest import mock

from aiohttp import web
import pytest

import webhook
from webhook import create_app, update_repo, verify_signature


run_check = functools.partial(subprocess.run, check=True)


async def test_signature(monkeypatch):
    """Test that signature verification fails and works as expected."""
    with pytest.raises(web.HTTPBadRequest,
                       match='Secret for non-existent was not set'):
        await verify_signature(b'unused', 'unused', 'non-existent', 'unused')

    monkeypatch.setenv('WEBHOOK_REPO_SECRET', 'abcdef')
    with pytest.raises(web.HTTPBadRequest, match='signature was invalid'):
        await verify_signature(b'unused', 'sha256=incorrect', 'repo', 'unused')

    # Signature found by passing data to `openssl dgst -sha256 -hmac $SECRET`.
    monkeypatch.setenv('WEBHOOK_REPO_SECRET', 'abcdef')
    await verify_signature(
        b'{"data": "foo"}',
        'sha256='
        'ebf35862e15f2ac2aa1339ebefff9a88b8270fc8a33dec8f756a398036d86329',
        'repo',
        'unused')


async def test_update_repo(tmp_path_factory):
    """Test that updating a repository works as expected."""
    # Set up a source repository.
    src = tmp_path_factory.mktemp('src')
    run_check(['git', 'init', '-b', 'gh-pages', src])
    (src / 'readme.txt').write_text('Test repo information')
    run_check(['git', 'add', 'readme.txt'], cwd=src)
    run_check(['git', 'commit', '-m', 'Initial commit'], cwd=src)

    # Make second from the first.
    dest = tmp_path_factory.mktemp('dest')
    run_check(['git', 'clone', src, dest])

    # Make a second commit in source repository.
    (src / 'install.txt').write_text('There is no installation.')
    run_check(['git', 'add', 'install.txt'], cwd=src)
    run_check(['git', 'commit', '-m', 'Add install information'], cwd=src)
    src_stdout = run_check(['git', 'show-ref', '--head', 'HEAD'], cwd=src,
                           capture_output=True).stdout.splitlines()
    src_commit = next(
        (line for line in src_stdout if line.split()[-1] == 'HEAD'), '')

    # Now this should correctly update the first repository.
    assert await update_repo(dest, 'unused', 'matplotlib/dest')
    dest_stdout = run_check(['git', 'show-ref', '--head', 'HEAD'], cwd=dest,
                            capture_output=True).stdout.splitlines()
    dest_commit = next(
        (line for line in dest_stdout if line.split()[-1] == 'HEAD'), '')
    assert dest_commit == src_commit


async def test_github_webhook_errors(aiohttp_client, monkeypatch):
    """Test invalid inputs to webhook."""
    client = await aiohttp_client(create_app())

    # Only /gh/<repo-name> exists.
    resp = await client.get('/')
    assert resp.status == 404
    resp = await client.get('/gh')
    assert resp.status == 404

    # Not allowed if missing correct headers.
    resp = await client.get('/gh/non-existent-repo')
    assert resp.status == 405
    resp = await client.post('/gh/non-existent-repo')
    assert resp.status == 400
    assert 'No delivery' in await resp.text()
    resp = await client.post('/gh/non-existent-repo',
                             headers={'X-GitHub-Delivery': 'foo'})
    assert resp.status == 400
    assert 'No signature' in await resp.text()

    monkeypatch.setattr(webhook, 'verify_signature',
                        mock.Mock(verify_signature, return_value=True))

    valid_headers = {
        'X-GitHub-Delivery': 'foo',
        'X-Hub-Signature-256': 'unused',
        'X-GitHub-Event': 'ping',
    }

    # Data should be JSON.
    resp = await client.post('/gh/non-existent-repo', headers=valid_headers,
                             data='}{')
    assert resp.status == 400
    assert 'Invalid data input' in await resp.text()

    # Some data fields are required.
    resp = await client.post('/gh/non-existent-repo', headers=valid_headers,
                             data='{}')
    assert resp.status == 400
    assert 'Missing required fields' in await resp.text()

    resp = await client.post(
        '/gh/non-existent-repo', headers=valid_headers,
        data='{"sender": {"login": "QuLogic"},'
             ' "repository": {"name": "foo", "owner": {"login": "foo"}}}')
    assert resp.status == 400
    assert 'incorrect organization' in await resp.text()

    resp = await client.post(
        '/gh/non-existent-repo', headers=valid_headers,
        data='{"sender": {"login": "QuLogic"}, "repository":'
             ' {"name": "foo", "owner": {"login": "matplotlib"}}}')
    assert resp.status == 400
    assert 'incorrect repository' in await resp.text()

    # Problem on our side.
    resp = await client.post(
        '/gh/non-existent',
        headers={**valid_headers, 'X-GitHub-Event': 'push'},
        data='{"sender": {"login": "QuLogic"}, "ref": "refs/heads/gh-pages", '
             '"repository": {"name": "non-existent", '
             '"owner": {"login": "matplotlib"}}}')
    assert resp.status == 500
    assert 'non-existent does not exist' in await resp.text()


async def test_github_webhook_valid(aiohttp_client, monkeypatch, tmp_path):
    """Test valid input to webhook."""
    client = await aiohttp_client(create_app())

    # Do no actual work, since that's tested above.
    monkeypatch.setattr(webhook, 'verify_signature',
                        mock.Mock(verify_signature, return_value=True))
    monkeypatch.setenv('SITE_DIR', str(tmp_path))
    ur_mock = mock.Mock(update_repo, return_value=None)
    monkeypatch.setattr(webhook, 'update_repo', ur_mock)

    valid_headers = {
        'X-GitHub-Delivery': 'foo',
        'X-Hub-Signature-256': 'unused',
    }

    # Ping event just returns success.
    resp = await client.post(
        '/gh/non-existent-repo',
        headers={**valid_headers, 'X-GitHub-Event': 'ping'},
        data='{"sender": {"login": "QuLogic"}, "hook_id": 1234,'
             ' "zen": "Beautiful is better than ugly.",'
             ' "repository": {"name": "non-existent-repo",'
             ' "owner": {"login": "matplotlib"}}}')
    assert resp.status == 200
    ur_mock.assert_not_called()

    # Push event to main branch should do nothing.
    resp = await client.post(
        '/gh/non-existent-repo',
        headers={**valid_headers, 'X-GitHub-Event': 'push'},
        data='{"sender": {"login": "QuLogic"},'
             ' "ref": "refs/heads/main",'
             ' "repository": {"name": "non-existent-repo",'
             ' "owner": {"login": "matplotlib"}}}')
    assert resp.status == 200
    ur_mock.assert_not_called()

    # Push event to gh-pages branch should run an update.
    tmp_repo = tmp_path / 'non-existent-repo'
    (tmp_repo / '.git').mkdir(parents=True, exist_ok=True)
    resp = await client.post(
        '/gh/non-existent-repo',
        headers={**valid_headers, 'X-GitHub-Event': 'push'},
        data='{"sender": {"login": "QuLogic"},'
             ' "ref": "refs/heads/gh-pages",'
             ' "repository": {"name": "non-existent-repo",'
             ' "owner": {"login": "matplotlib"}}}')
    assert resp.status == 200
    ur_mock.assert_called_once_with(
        tmp_repo, 'foo', 'matplotlib/non-existent-repo')
