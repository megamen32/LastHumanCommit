#!/usr/bin/env python3
"""Run on the selected Mac only; alter the dedicated synthetic fixture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['raw-edit', 'offline-revise', 'verify'])
parser.add_argument('--marker', required=True)
args = parser.parse_args()
base = Path.home() / '.local/share/lhc-plan-mirror'
plan = base / 'consumer-plan'
state = plan / '.lhc-publication'
if args.action in ('raw-edit', 'offline-revise'):
    path = plan / 'leaves/H01.json'
    leaf = json.loads(path.read_text())
    leaf['note'] = args.marker
    path.write_text(json.dumps(leaf, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'raw_save': True, 'marker': args.marker}))
if args.action == 'offline-revise':
    env = dict(os.environ)
    env.pop('LHC_PLAN_MIRROR_CONFIG', None)
    start = time.monotonic()
    result = subprocess.run([sys.executable, str(base / 'current/tools/lhc_plan_publish.py'),
                             'revise', str(plan), '--reason', args.marker],
                            env=env, capture_output=True, text=True, timeout=8)
    print(json.dumps({'local_revise_rc': result.returncode,
                      'seconds': round(time.monotonic() - start, 3),
                      'without_environment_override': True,
                      'revision_count': len(list((state / 'revisions').glob('r*.json')))}))
    if result.returncode:
        print(result.stderr[:1000])
        raise SystemExit(1)
if args.action == 'verify':
    mirror = json.loads((state / 'mirror-state.json').read_text())
    receipt = mirror.get('server_receipt', {})
    url = receipt.get('url')
    page = urllib.request.urlopen(url, timeout=10).read().decode()
    found = args.marker in page
    print(json.dumps({'url': url, 'marker_visible': found,
                      'seq': mirror.get('seq'), 'receipt_seq': receipt.get('seq'),
                      'last_successful_sync': mirror.get('last_successful_sync'),
                      'revision_count': len(list((state / 'revisions').glob('r*.json')))}))
    raise SystemExit(0 if found else 1)
