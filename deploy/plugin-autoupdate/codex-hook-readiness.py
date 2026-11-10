#!/usr/bin/env python3
"""Read native Codex hook readiness without changing trust or configuration."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

PLUGIN = 'last-human-commit@megamen32-plugins'


def assess(result):
    """Return conservative readiness and the native evidence for this plugin."""
    data = result.get('data')
    if not isinstance(data, list) or not data:
        raise ValueError('hooks/list returned no cwd data')
    hooks, warnings, errors = [], [], []
    for entry in data:
        if not isinstance(entry, dict) or not isinstance(entry.get('hooks'), list):
            raise ValueError('invalid hooks/list entry')
        for field, target in (('warnings', warnings), ('errors', errors)):
            value = entry.get(field, [])
            if not isinstance(value, list):
                raise ValueError('invalid hooks/list ' + field)
            target.extend(value)
        hooks.extend({**hook, 'cwd': entry.get('cwd')} for hook in entry['hooks']
                     if isinstance(hook, dict) and hook.get('pluginId') == PLUGIN)
    ready = bool(hooks) and all(hook.get('enabled') is True and
                                hook.get('trustStatus') == 'trusted' and
                                hook.get('key') and hook.get('currentHash')
                                for hook in hooks) and not warnings and not errors
    return {'status': 'READY' if ready else 'NEEDS_REVIEW', 'pluginId': PLUGIN,
            'hooks': hooks, 'warnings': warnings, 'errors': errors}


async def readback(codex_bin, cwd, timeout=10):
    async def exchange():
        process = await asyncio.create_subprocess_exec(
            codex_bin, 'app-server', '--stdio', cwd=str(cwd),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        async def send(message):
            process.stdin.write((json.dumps(message) + '\n').encode())
            await process.stdin.drain()
        async def response(request_id):
            while True:
                line = await process.stdout.readline()
                if not line:
                    raise ValueError('app-server closed before response')
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError('invalid app-server message')
                if message.get('id') == request_id:
                    if 'error' in message:
                        raise ValueError('app-server error: ' + json.dumps(message['error']))
                    if not isinstance(message.get('result'), dict):
                        raise ValueError('invalid app-server response')
                    return message['result']
        try:
            await send({'id': 1, 'method': 'initialize', 'params': {
                'clientInfo': {'name': 'lhc-hook-readiness', 'version': '1'},
                'capabilities': {'experimentalApi': True}}})
            await response(1)
            await send({'method': 'initialized', 'params': {}})
            await send({'id': 2, 'method': 'hooks/list', 'params': {'cwds': [str(cwd)]}})
            return assess(await response(2))
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()
    try:
        return await asyncio.wait_for(exchange(), timeout)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, asyncio.TimeoutError) as error:
        return {'status': 'ERROR', 'pluginId': PLUGIN, 'hooks': [], 'warnings': [],
                'errors': [str(error) or type(error).__name__]}


def check(codex_bin, cwd, timeout=10):
    return asyncio.run(readback(codex_bin, cwd, timeout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-bin', default='codex')
    parser.add_argument('--cwd', type=Path, default=Path.home())
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    result = check(args.codex_bin, args.cwd, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
