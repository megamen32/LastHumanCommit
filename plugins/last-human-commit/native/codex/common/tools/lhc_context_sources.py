#!/usr/bin/env python3
"""Read-only context resources from the current LHC package. No copied rule store."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

META_KEY = 'io.gptadmin/context-source'
MAX_BYTES = 256 * 1024
VERSION_RE = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')

def package_root() -> Path:
    configured = os.environ.get('LHC_CONTEXT_ROOT', '').strip()
    if configured:
        root = Path(configured)
        if not root.is_absolute():
            raise ValueError('LHC_CONTEXT_ROOT must be absolute')
        if VERSION_RE.fullmatch(root.name):
            root = root.parent
        if (root / 'AGENTS.md').is_file():
            return root.resolve(strict=True)
        versions = [d for d in root.iterdir() if d.is_dir() and not d.is_symlink() and VERSION_RE.fullmatch(d.name)]
        if not versions:
            raise ValueError('no installed LHC context package')
        return max(versions, key=lambda d: tuple(map(int, d.name.split('.')))).resolve(strict=True)
    for root in Path(__file__).resolve().parents:
        if (root / 'AGENTS.md').is_file() and ((root / 'common/config/context-sources.json').is_file() or (root / 'common/config/context-sources.json').is_file()):
            return root
    raise ValueError('LHC context package is unavailable')

def bounded_text(path: Path, root: Path) -> str:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('context resource escapes its package or is not a file')
    with resolved.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError('context resource is empty or exceeds size limit')
    return data.decode('utf-8', errors='strict')

def package_version(root: Path) -> str:
    for relative in ['.claude-plugin/plugin.json', '.codex-plugin/plugin.json', 'plugin.json']:
        path = root / relative
        if path.is_file():
            return str(json.loads(bounded_text(path, root)).get('version') or 'unversioned')
    version = root / 'VERSION'
    return bounded_text(version, root).strip() if version.is_file() else 'source'

def source_entries() -> tuple[Path, str, list[dict[str, Any]]]:
    root = package_root()
    common = root / ('src/common' if (root / 'common/config/context-sources.json').is_file() else 'common')
    manifest = json.loads(bounded_text(common / 'config/context-sources.json', root))
    entries = manifest.get('sources')
    if manifest.get('schema_version') != 1 or not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise ValueError('invalid context sources manifest')
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ['id','uri','title','path']):
            raise ValueError('invalid context source descriptor')
        if not item['uri'].startswith('lhc://context/') or item['uri'] in seen:
            raise ValueError('invalid or duplicate context resource URI')
        seen.add(item['uri'])
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('invalid context source path')
    return root, package_version(root), entries

def resource_content(root: Path, item: dict[str, Any]) -> str:
    path = item['path']
    if path.startswith('common/') and (root / 'src/common').is_dir():
        path = 'src/' + path
    return bounded_text(root / path, root)

def resource_descriptor(item: dict[str, Any], text: str, version: str) -> dict[str, Any]:
    data = text.encode('utf-8')
    return {'uri':item['uri'], 'name':item['id'], 'title':item['title'],
            'description':item.get('description',''), 'mimeType':item.get('mime_type','text/markdown'),
            'size':len(data), 'annotations':{'audience':['assistant'], 'priority':1 if item.get('default_selected') else 0.5},
            '_meta':{META_KEY:{'schema_version':1,'id':item['id'],'version':version,
                     'sha256':hashlib.sha256(data).hexdigest(), 'default_selected':bool(item.get('default_selected'))}}}

def list_resources() -> dict[str, Any]:
    root, version, entries = source_entries()
    return {'resources':[resource_descriptor(item, resource_content(root,item), version) for item in entries]}

def read_resource(uri: str) -> dict[str, Any]:
    root, version, entries = source_entries()
    item = next((item for item in entries if item['uri'] == uri), None)
    if item is None:
        raise ValueError('unknown LHC context resource')
    text = resource_content(root,item)
    descriptor = resource_descriptor(item,text,version)
    return {'contents':[{'uri':uri,'mimeType':descriptor['mimeType'],'text':text,'_meta':descriptor['_meta']}]}
