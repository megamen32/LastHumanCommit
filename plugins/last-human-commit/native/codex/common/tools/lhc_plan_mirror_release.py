#!/usr/bin/env python3
"""Release tool of the plan mirror: status | build | canary | switch | rollback.

A release is an immutable copy of the installed LHC tools in
<base>/releases/<16 hex>/tools, where the name is sha256 over the relative
names and bytes of every *.py (the same rule as deploy/plan-mirror/install-native.py).
The services (systemd --user: lhc-plan-mirror = serve, lhc-plan-observer = watch)
carry the release path in their units; <base>/current is a convenience link.

build never switches. canary runs a release on a spare port with a temporary
directory and a copy of a plan. switch backs up config, registry and units,
rewrites the units, then: stop watch, restart serve, start watch. It never
touches ingest.lock. rollback switches back to the previous release.
Names and paths come from arguments, or from <config>/release.json, or the
defaults of this host.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime

HOME = Path.home()
DEFAULTS = {
    "base": str(HOME / ".local/share/lhc-plan-mirror"),
    "config_dir": str(HOME / ".config/lhc/plan-mirror"),
    "units_dir": str(HOME / ".config/systemd/user"),
    "mirror_unit": "lhc-plan-mirror.service",
    "observer_unit": "lhc-plan-observer.service",
    "systemctl": "systemctl --user",
    "python": "/usr/bin/python3",
    "canary_port": 18769,
}
RELEASE_ID = re.compile(r"^[0-9a-f]{16}$")
SECRET_FILES = {"write-token"}  # a backup never duplicates the protected token


class ReleaseError(RuntimeError):
    pass


def run_command(argv, *, timeout=60):
    """The only place that starts systemctl; tests replace it."""
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def settings(args):
    config_dir = Path(args.config_dir or DEFAULTS["config_dir"]).expanduser()
    saved = {}
    path = config_dir / "release.json"
    if path.is_file():
        saved = json.loads(path.read_text())
    out = {}
    for key, default in DEFAULTS.items():
        value = getattr(args, key, None)
        out[key] = value if value is not None else saved.get(key, default)
    out["config_dir"] = Path(out["config_dir"]).expanduser()
    out["base"] = Path(out["base"]).expanduser()
    out["units_dir"] = Path(out["units_dir"]).expanduser()
    out["canary_port"] = int(out["canary_port"])
    if not Path(out["python"]).exists():
        out["python"] = sys.executable
    return out


# ---- release identity -------------------------------------------------------

def tools_hash(tools):
    tools = Path(tools)
    digest = hashlib.sha256()
    files = sorted(tools.rglob("*.py"))
    if not any(item.name == "lhc_plan_mirror.py" for item in files):
        raise ReleaseError(f"{tools}: нет lhc_plan_mirror.py")
    for item in files:
        digest.update(str(item.relative_to(tools)).encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()[:16]


def release_dir(cfg, release):
    if not RELEASE_ID.match(release):
        raise ReleaseError(f"неверный идентификатор релиза: {release}")
    return cfg["base"] / "releases" / release


def verify_release(cfg, release):
    tools = release_dir(cfg, release) / "tools"
    if not tools.is_dir():
        raise ReleaseError(f"релиз {release} не собран")
    actual = tools_hash(tools)
    if actual != release:
        raise ReleaseError(f"релиз {release} изменён: хэш содержимого {actual}")
    return tools


def default_source():
    return Path(__file__).resolve().parent


# ---- state ------------------------------------------------------------------

def state_path(cfg):
    return cfg["base"] / "release-state.json"


def read_state(cfg):
    path = state_path(cfg)
    if path.is_file():
        return json.loads(path.read_text())
    return {"current": current_link(cfg), "previous": []}


def write_state(cfg, state):
    path = state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    os.replace(temporary, path)


def current_link(cfg):
    link = cfg["base"] / "current"
    if link.is_symlink():
        name = Path(os.readlink(link)).name
        return name if RELEASE_ID.match(name) else None
    return None


def set_current(cfg, release):
    link = cfg["base"] / "current.next"
    link.unlink(missing_ok=True)
    link.symlink_to(release_dir(cfg, release))
    os.replace(link, cfg["base"] / "current")


@contextlib.contextmanager
def release_lock(cfg):
    cfg["base"].mkdir(parents=True, exist_ok=True)
    with (cfg["base"] / "release.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ReleaseError("другая смена релиза уже идёт")
        yield


# ---- units ------------------------------------------------------------------

def unit_text(cfg, release, role):
    tools = release_dir(cfg, release) / "tools" / "lhc_plan_mirror.py"
    if role == "mirror":
        command = [cfg["python"], str(tools), "serve", "--config", str(cfg["config_dir"] / "server.json")]
        description = "LHC plan mirror"
    else:
        command = [cfg["python"], str(tools), "watch", "--config", str(cfg["config_dir"] / "client.json")]
        description = "LHC plan observer"
    argv = " ".join('"' + v.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"') + '"' for v in command)
    return (f"[Unit]\nDescription={description}\nAfter=network.target\n\n[Service]\nType=simple\n"
            f"WorkingDirectory={release_dir(cfg, release)}\nExecStart={argv}\nRestart=on-failure\n"
            "RestartSec=5\nUMask=0077\nNoNewPrivileges=true\n\n[Install]\nWantedBy=default.target\n")


def unit_files(cfg):
    return {"mirror": cfg["units_dir"] / cfg["mirror_unit"], "observer": cfg["units_dir"] / cfg["observer_unit"]}


def unit_release(path):
    if not path.is_file():
        return None
    found = re.search(r"/releases/([0-9a-f]{16})/", path.read_text())
    return found.group(1) if found else None


def write_unit(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def systemctl(cfg, *words, check=True):
    code, output = run_command([*cfg["systemctl"].split(), *words])
    if check and code != 0:
        raise ReleaseError(f"systemctl {' '.join(words)}: код {code}")
    return code, output.strip()


def service_state(cfg, unit):
    code, output = systemctl(cfg, "is-active", unit, check=False)
    return output.splitlines()[0] if output else ("active" if code == 0 else "unknown")


# ---- commands ---------------------------------------------------------------

def cmd_status(cfg, args):
    releases = release_dir(cfg, "0" * 16).parent
    existing = sorted(p.name for p in releases.iterdir() if RELEASE_ID.match(p.name)) if releases.is_dir() else []
    source = Path(args.source).resolve() if args.source else default_source()
    try:
        candidate = tools_hash(source)
    except (ReleaseError, OSError):
        candidate = None
    state = read_state(cfg)
    files = unit_files(cfg)
    return {
        "current": current_link(cfg), "previous": state.get("previous", []),
        "source_hash": candidate, "source_built": candidate in existing,
        "releases": existing,
        "units": {role: {"file": str(path), "release": unit_release(path),
                         "state": service_state(cfg, path.name)} for role, path in files.items()},
    }


def cmd_build(cfg, args):
    source = Path(args.source).resolve() if args.source else default_source()
    release = tools_hash(source)
    target = release_dir(cfg, release)
    if target.exists():
        verify_release(cfg, release)
        return {"release": release, "path": str(target), "built": False}
    stage = target.parent / f".build-{release}-{os.getpid()}"
    shutil.rmtree(stage, ignore_errors=True)
    try:
        for item in sorted(source.rglob("*.py")):
            copy = stage / "tools" / item.relative_to(source)
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, copy)
        if tools_hash(stage / "tools") != release:
            raise ReleaseError("копия не совпала с источником по хэшу")
        os.replace(stage, target)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return {"release": release, "path": str(target), "built": True}


def free_port(port):
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def http_get(url, token=None, timeout=3):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token} if token else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def cmd_canary(cfg, args):
    release = args.release or tools_hash(Path(args.source).resolve() if args.source else default_source())
    tools = verify_release(cfg, release)
    port = cfg["canary_port"]
    if not free_port(port):
        raise ReleaseError(f"порт {port} занят: канарейка ничего не запускала")
    token = "c" * 32
    with tempfile.TemporaryDirectory(prefix="lhc-mirror-canary-") as tmp:
        tmp = Path(tmp)
        plan = tmp / "plan"
        if args.plan:
            shutil.copytree(args.plan, plan, ignore=shutil.ignore_patterns(".lhc-publication", "plan.html", "plan.md"))
        else:
            (plan / "leaves").mkdir(parents=True)
            (plan / "plan.json").write_text(json.dumps({"title": "Canary", "goal": "release check", "slots": 1}))
            (plan / "leaves/A.json").write_text(json.dumps(
                {"id": "A", "label": "canary", "status": "queued", "estimate_minutes": 10}))
        (tmp / "token").write_text(token + "\n")
        os.chmod(tmp / "token", 0o600)
        (tmp / "key").write_text("k" * 32 + "\n")
        os.chmod(tmp / "key", 0o600)
        endpoint = f"http://127.0.0.1:{port}"
        server = {"listen": "127.0.0.1", "port": port, "data_dir": str(tmp / "server"), "webroot": str(tmp / "web"),
                  "base_url": "https://canary.invalid", "token_file": str(tmp / "token"),
                  "dashboard_key_file": str(tmp / "key")}
        client = {"mode": "mirror", "endpoint": endpoint, "base_url": server["base_url"], "token_file": str(tmp / "token"),
                  "data_dir": str(tmp / "client"), "plans": [str(plan)], "poll_seconds": 1,
                  "debounce_seconds": 0.1, "timeout_seconds": 3}
        (tmp / "server.json").write_text(json.dumps(server))
        (tmp / "client.json").write_text(json.dumps(client))
        env = {**os.environ, "HOME": str(tmp), "LHC_PLAN_MIRROR_CONFIG": str(tmp / "client.json")}
        entry = str(tools / "lhc_plan_mirror.py")
        log = (tmp / "serve.log").open("w")
        process = subprocess.Popen([cfg["python"], entry, "serve", "--config", str(tmp / "server.json")],
                                   env=env, stdout=log, stderr=log, cwd=str(tools.parent))
        try:
            deadline = time.monotonic() + 20
            while True:
                try:
                    http_get(endpoint + "/health")
                    break
                except OSError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise ReleaseError("канарейка: serve не поднялся: " + (tmp / "serve.log").read_text()[-300:])
                    time.sleep(0.2)
            steps = {}
            for name in ("register", "once"):
                argv = [cfg["python"], entry, name] + ([str(plan)] if name == "register" else []) + ["--config", str(tmp / "client.json")]
                done = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=90, cwd=str(tools.parent))
                if done.returncode != 0:
                    raise ReleaseError(f"канарейка: {name} завершился кодом {done.returncode}: {done.stderr[-200:]}")
                steps[name] = "ok"
            receipts = json.loads(http_get(endpoint + "/v1/status", token)).get("plans", [])
            if not receipts:
                raise ReleaseError("канарейка: сервер не принял снимок плана")
            parts = receipts[0]["url"].rstrip("/").split("/")[-2:]
            page = tmp / "web" / parts[0] / parts[1] / "index.html"
            if not page.is_file() or page.stat().st_size == 0:
                raise ReleaseError("канарейка: HTML плана не собрался")
        finally:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
            log.close()
    return {"release": release, "port": port, "steps": steps, "receipt_seq": receipts[0]["seq"], "html": True}


def backup(cfg):
    stamp = datetime.now().strftime("%Y%m%d")
    target = cfg["base"] / f"backup-{stamp}"
    counter = 1
    while target.exists():
        counter += 1
        target = cfg["base"] / f"backup-{stamp}-{datetime.now().strftime('%H%M%S')}-{counter}"
    (target / "config").mkdir(parents=True, mode=0o700)
    (target / "units").mkdir(mode=0o700)
    for item in cfg["config_dir"].iterdir() if cfg["config_dir"].is_dir() else []:
        if item.is_file() and item.name not in SECRET_FILES:
            shutil.copy2(item, target / "config" / item.name)
    registry = cfg["base"] / "client" / "registry.json"
    if registry.is_file():
        shutil.copy2(registry, target / "registry.json")
    for path in unit_files(cfg).values():
        if path.is_file():
            shutil.copy2(path, target / "units" / path.name)
    return target


def apply_release(cfg, release):
    """Units, link, then: stop watch, restart serve, start watch. ingest.lock is never touched."""
    verify_release(cfg, release)
    files = unit_files(cfg)
    write_unit(files["mirror"], unit_text(cfg, release, "mirror"))
    write_unit(files["observer"], unit_text(cfg, release, "observer"))
    set_current(cfg, release)
    systemctl(cfg, "daemon-reload")
    systemctl(cfg, "stop", cfg["observer_unit"])
    systemctl(cfg, "restart", cfg["mirror_unit"])
    systemctl(cfg, "start", cfg["observer_unit"])
    for unit in (cfg["mirror_unit"], cfg["observer_unit"]):
        if service_state(cfg, unit) != "active":
            raise ReleaseError(f"{unit} не active после смены релиза")


def switch_to(cfg, release, *, rollback=False):
    verify_release(cfg, release)
    with release_lock(cfg):
        state = read_state(cfg)
        before = state.get("current") or current_link(cfg) or unit_release(unit_files(cfg)["mirror"])
        saved = backup(cfg)
        try:
            apply_release(cfg, release)
        except Exception as error:
            if before and before != release:
                try:
                    apply_release(cfg, before)
                except Exception as second:
                    raise ReleaseError(f"смена на {release} не удалась ({error}); возврат на {before} тоже: {second}")
                raise ReleaseError(f"смена на {release} не удалась ({error}); возвращён {before}")
            raise
        previous = list(state.get("previous", []))
        if not rollback and before and before != release:
            previous.append(before)
        write_state(cfg, {"current": release, "previous": previous})
    return {"release": release, "from": before, "backup": str(saved),
            "units": {role: unit_release(path) for role, path in unit_files(cfg).items()}}


def cmd_switch(cfg, args):
    release = args.release or tools_hash(Path(args.source).resolve() if args.source else default_source())
    if args.canary:
        cmd_canary(cfg, argparse.Namespace(release=release, source=args.source, plan=args.plan))
    return switch_to(cfg, release)


def cmd_rollback(cfg, args):
    state = read_state(cfg)
    previous = list(state.get("previous", []))
    target = args.to or (previous[-1] if previous else None)
    if not target:
        raise ReleaseError("нет предыдущего релиза; укажи --to <хэш>")
    result = switch_to(cfg, target, rollback=True)
    if not args.to and previous:
        previous.pop()
    write_state(cfg, {"current": target, "previous": previous})
    return result


def parser():
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for key in ("base", "config_dir", "units_dir", "mirror_unit", "observer_unit", "systemctl", "python", "canary_port"):
        top.add_argument("--" + key.replace("_", "-"), dest=key, default=None)
    commands = top.add_subparsers(dest="command", required=True)
    for name in ("status", "build", "canary", "switch", "rollback"):
        cmd = commands.add_parser(name)
        if name in ("status", "build", "canary", "switch"):
            cmd.add_argument("--source", help="каталог tools; по умолчанию каталог этого файла")
        if name in ("canary", "switch"):
            cmd.add_argument("release", nargs="?", help="хэш релиза; по умолчанию хэш источника")
            cmd.add_argument("--plan", help="каталог плана для копии канарейки")
        if name == "switch":
            cmd.add_argument("--canary", action="store_true", help="сначала канарейка")
        if name == "rollback":
            cmd.add_argument("--to", help="хэш релиза; по умолчанию предыдущий")
    return top


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        cfg = settings(args)
        result = {"status": cmd_status, "build": cmd_build, "canary": cmd_canary,
                  "switch": cmd_switch, "rollback": cmd_rollback}[args.command](cfg, args)
    except (ReleaseError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"LHC: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
