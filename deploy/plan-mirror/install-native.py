#!/usr/bin/env python3
"""Install only the dedicated LHC mirror and observer native services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import secrets
import shutil
import subprocess
import sys
import time


def write_private(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(path, 'w', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', required=True, type=Path)
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--endpoint', default='https://lhc.bezrabotnyi.com')
    parser.add_argument('--plan', action='append', default=[])
    parser.add_argument('--root', action='append', default=[])
    args = parser.parse_args()
    source = args.tools.resolve()
    if args.server and sys.platform == 'darwin':
        parser.error('Central server is authorized only on server100')
    if not args.prepare_only and not (source / 'lhc_plan_mirror.py').is_file():
        parser.error('Core entry point is not ready; nothing installed')
    home = Path.home()
    base = home / '.local/share/lhc-plan-mirror'
    config = home / '.config/lhc/plan-mirror'
    config.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(config, 0o700)
    digest = hashlib.sha256()
    files = sorted(source.rglob('*.py'))
    for item in files:
        digest.update(str(item.relative_to(source)).encode())
        digest.update(item.read_bytes())
    release = base / 'releases' / digest.hexdigest()[:16]
    if not args.prepare_only and not release.exists():
        for item in files:
            target = release / 'tools' / item.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    token = config / 'write-token'
    if args.server and not token.exists():
        write_private(token, secrets.token_urlsafe(48) + '\n')
    if not token.is_file():
        parser.error('Transfer the existing protected write-token first')
    os.chmod(token, 0o600)
    client = {
        'mode': 'mirror', 'endpoint': args.endpoint,
        'base_url': 'https://lhc.bezrabotnyi.com', 'token_file': str(token),
        'data_dir': str(base / 'client'), 'plans': args.plan, 'roots': args.root,
        'poll_seconds': 1, 'debounce_seconds': 1, 'timeout_seconds': 3,
    }
    write_private(config / 'client.json', json.dumps(client, indent=2) + '\n')
    commands = {'observer': [sys.executable, str(release / 'tools/lhc_plan_mirror.py'),
                             'watch', '--config', str(config / 'client.json')]}
    if args.server:
        key = config / 'dashboard-key'
        if not key.exists():
            write_private(key, secrets.token_urlsafe(32) + '\n')
        os.chmod(key, 0o600)
        server = {
            'listen': '127.0.0.1', 'port': 8769, 'data_dir': str(base / 'server'),
            'webroot': '/var/www/lhc', 'base_url': client['base_url'],
            'token_file': str(token), 'dashboard_key_file': str(key),
        }
        write_private(config / 'server.json', json.dumps(server, indent=2) + '\n')
        write_private(config / 'dashboard-url', client['base_url'] + '/dashboard/' + key.read_text().strip() + '/\n')
        commands['mirror'] = [sys.executable, str(release / 'tools/lhc_plan_mirror.py'),
                              'serve', '--config', str(config / 'server.json')]
    if args.prepare_only:
        print(json.dumps({'config': str(config), 'status': 'prepared; not running'}))
        return
    if sys.platform == 'darwin':
        log = base / 'logs'
        log.mkdir(parents=True, exist_ok=True)
        plist = home / 'Library/LaunchAgents/com.lhc.plan-observer.plist'
        plist.parent.mkdir(parents=True, exist_ok=True)
        payload = {'Label': 'com.lhc.plan-observer', 'ProgramArguments': commands['observer'],
                   'WorkingDirectory': str(release), 'RunAtLoad': True, 'KeepAlive': True,
                   'ThrottleInterval': 5, 'Umask': 0o077,
                   'StandardOutPath': str(log / 'observer.stdout.log'),
                   'StandardErrorPath': str(log / 'observer.stderr.log')}
        write_private(plist, plistlib.dumps(payload).decode())
        target = f'gui/{os.getuid()}'
        subprocess.run(['launchctl', 'bootout', target + '/com.lhc.plan-observer'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # launchd may still be tearing down the old registration after bootout.
        # Check only return codes; print output can contain inherited secrets.
        service = target + '/com.lhc.plan-observer'
        for attempt in range(6):
            alive = subprocess.run(['launchctl', 'print', service],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if alive.returncode == 0:
                time.sleep(1)
                continue
            loaded = subprocess.run(['launchctl', 'bootstrap', target, str(plist)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if loaded.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Observer launchd replacement failed; inspect filtered state only')
    else:
        units = home / '.config/systemd/user'
        units.mkdir(parents=True, exist_ok=True)
        for role, command in commands.items():
            name = 'lhc-plan-' + role + '.service'
            # systemd does not invoke a shell. Escape specifiers and argument quotes.
            argv = ' '.join('"' + value.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"') + '"' for value in command)
            write_private(units / name, f'''[Unit]
Description=LHC plan {role}
After=network.target

[Service]
Type=simple
WorkingDirectory={release}
ExecStart={argv}
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true

[Install]
WantedBy=default.target
''')
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        for role in commands:
            name = 'lhc-plan-' + role + '.service'
            subprocess.run(['systemctl', '--user', 'enable', name], check=True)
            subprocess.run(['systemctl', '--user', 'restart', name], check=True)
    link = base / 'current.next'
    link.unlink(missing_ok=True)
    link.symlink_to(release)
    link.replace(base / 'current')
    print(json.dumps({'runtime': str(release), 'config': str(config),
                      'services': list(commands), 'status': 'installed; verify live separately'}))


if __name__ == '__main__':
    main()
