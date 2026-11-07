"""HTTP MCP client for the already configured, process-owned Herder singleton.

Credential resolution follows Herder's fleet-direct bridge. It never launches a
server, writes credentials, follows redirects or retries a mutating request.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import stat
import urllib.error
import urllib.parse
import urllib.request
import uuid


class TransportError(RuntimeError):
    """Fixed, secret-free reason; submitted marks an uncertain tool request."""
    def __init__(self, reason, *, submitted=False):
        super().__init__(reason)
        self.reason = reason
        self.submitted = submitted


def _protected_read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                or before.st_mode & 0o077 or before.st_size > 65536):
            raise TransportError('herder_credential_unverified')
        content = stream.read(65537)
        after = os.fstat(stream.fileno())
        keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')
        if any(getattr(before, k) != getattr(after, k) for k in keys):
            raise TransportError('herder_credential_unverified')
        return content


def existing_token(environ=None, config_dir=None):
    """Read the existing Herder environment and fingerprint-backed secret."""
    env = os.environ if environ is None else environ
    directory = Path(config_dir) if config_dir else Path.home() / '.config/agent-herder'
    value = env.get('AGENT_HERDER_HTTP_TOKEN', '').strip()
    try:
        if not value:
            for line in _protected_read(directory / 'herder.env').splitlines():
                match = re.fullmatch(r'\s*(?:export\s+)?AGENT_HERDER_HTTP_TOKEN\s*=\s*(.*?)\s*', line)
                if match:
                    parts = shlex.split(match.group(1), comments=True, posix=True)
                    if len(parts) != 1:
                        raise TransportError('herder_credential_unverified')
                    value = parts[0]
        if re.fullmatch(r'sha256:[0-9a-f]{16}', value):
            store = json.loads(_protected_read(directory / 'secrets.json'))
            secret = store.get('secrets', {}).get('AGENT_HERDER_HTTP_TOKEN')
            if not isinstance(secret, str) or not secret:
                raise TransportError('herder_credential_missing')
            if 'sha256:' + hashlib.sha256(secret.encode()).hexdigest()[:16] != value:
                raise TransportError('herder_credential_unverified')
            value = secret
    except FileNotFoundError:
        raise TransportError('herder_credential_missing') from None
    except TransportError:
        raise
    except Exception:
        raise TransportError('herder_credential_unverified') from None
    if not value:
        raise TransportError('herder_credential_missing')
    if len(value) > 4096 or not re.fullmatch(r'[!-~]+', value):
        raise TransportError('herder_credential_unverified')
    return value


def unwrap_tool(value):
    if not isinstance(value, dict):
        raise TransportError('herder_tool_payload_invalid', submitted=True)
    if isinstance(value.get('structuredContent'), dict):
        result = value['structuredContent']
    elif isinstance(value.get('content'), list):
        texts = [x.get('text') for x in value['content'] if x.get('type') == 'text']
        if len(texts) != 1:
            raise TransportError('herder_tool_payload_invalid', submitted=True)
        try:
            result = json.loads(texts[0])
        except (ValueError, TypeError):
            raise TransportError('herder_tool_payload_invalid', submitted=True) from None
    else:
        result = value
    if not isinstance(result, dict):
        raise TransportError('herder_tool_payload_invalid', submitted=True)
    if value.get('isError'):
        # A generic tool error is not evidence that admission never happened.
        return dict(result, isError=True)
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HerderMcpClient:
    """A bounded connection to the existing loopback singleton, no polling."""
    def __init__(self, *, url=None, token=None, host_id=None, timeout=10, deliver_timeout=60, environ=None):
        env = os.environ if environ is None else environ
        self.url = url or env.get('AGENT_HERDER_HTTP_URL', 'http://127.0.0.1:18787/mcp')
        parsed = urllib.parse.urlsplit(self.url)
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path != '/mcp'):
            raise TransportError('herder_loopback_endpoint_required')
        self._token = token
        self._env = env
        self.host_id = host_id or socket.gethostname()
        self.timeout = timeout
        # Native Codex admission allows a 30s RPC after preparation/quota reads.
        # Leave delivery headroom without extending init/metadata read bounds.
        self.deliver_timeout = deliver_timeout
        self._session = None
        self._initialized = False
        # A process-wide proxy must not receive the singleton credential.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def _rpc(self, method, params):
        identity = str(uuid.uuid4())
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params}
        notify = method.startswith('notifications/')
        if not notify:
            payload['id'] = identity
        if self._token is None:
            self._token = existing_token(self._env)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': '2025-11-25', 'Authorization': 'Bearer ' + self._token}
        if self._session:
            headers['Mcp-Session-Id'] = self._session
        submitted = method == 'tools/call'
        timeout = self.deliver_timeout if submitted and params.get('name') == 'deliver' else self.timeout
        try:
            response = self._opener.open(urllib.request.Request(self.url, json.dumps(payload).encode(), headers), timeout=timeout)
            with response:
                if method == 'initialize':
                    self._session = response.headers.get('Mcp-Session-Id')
                if notify:
                    return {}
                data = b''
                while True:
                    chunk = response.read1(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 1048576:
                        raise TransportError('herder_response_limit', submitted=submitted)
                    if 'text/event-stream' in response.headers.get('Content-Type', ''):
                        for frame in data.replace(b'\r\n', b'\n').split(b'\n\n')[:-1]:
                            text = '\n'.join(l[5:].lstrip() for l in frame.decode().splitlines() if l.startswith('data:'))
                            try:
                                value = json.loads(text)
                            except ValueError:
                                continue
                            if value.get('id') == identity:
                                return self._checked(value, identity, submitted)
                return self._checked(json.loads(data), identity, submitted)
        except TransportError:
            raise
        except urllib.error.HTTPError as error:
            code = error.code
            error.close()
            raise TransportError('herder_http_' + str(code), submitted=submitted) from None
        except Exception:
            raise TransportError('herder_transport_unavailable', submitted=submitted) from None

    @staticmethod
    def _checked(value, identity, submitted):
        if not isinstance(value, dict) or value.get('id') != identity:
            raise TransportError('herder_rpc_identity_mismatch', submitted=submitted)
        if value.get('error'):
            raise TransportError('herder_rpc_error', submitted=submitted)
        return value.get('result', {})

    def call(self, name, arguments):
        if not self._initialized:
            self._rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                      'clientInfo': {'name': 'lhc-execution', 'version': '1'}})
            self._rpc('notifications/initialized', {})
            self._initialized = True
        return unwrap_tool(self._rpc('tools/call', {'name': name, 'arguments': arguments}))
