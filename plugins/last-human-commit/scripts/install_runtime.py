#!/usr/bin/env python3
"""Point supported user instructions to a natively installed LHC package."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid

BEGIN="<!-- lhc-autoentry:begin -->"
END="<!-- lhc-autoentry:end -->"
OPENCODE_PLUGIN_FILES=("lhc-v2.ts",)

def backup_dir(home:Path)->Path:
    return home/".local/state/last-human-commit/backups"

def backup_path(home:Path,runtime:str,suffix:str="")->Path:
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
    return backup_dir(home)/(f"{stamp}-{runtime}{suffix}.md")

def register_opencode_mcp(home:Path,root:Path)->dict:
    """Give OpenCode the LHC plan tools: a local MCP server entry in its user config."""
    script=root/"scripts"/"plan_mcp.py"
    if not script.is_file():
        return {"mcp":"skipped","reason":"plan_mcp.py is missing from the installed package"}
    file=home/".config/opencode/opencode.json"
    config=json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {"$schema":"https://opencode.ai/config.json"}
    entry={"type":"local","command":["python3",str(script)],"enabled":True}
    if config.setdefault("mcp",{}).get("LhcPlan")==entry:
        return {"mcp":"unchanged","file":str(file)}
    if file.is_file():
        backup=backup_path(home,"opencode","-config")
        backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_text(file.read_text(encoding="utf-8"),encoding="utf-8")
    config["mcp"]["LhcPlan"]=entry
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"mcp":"registered","file":str(file)}

OPENCODE_ROLES={"Orchestrator":"LastHumanCommit Orchestrator: carries the owner's sessions to results from a registry and file mail; does not do the work.",
                "Sentinel":"LastHumanCommit Sentinel: watches one thing, reports only when something is wrong."}

def register_opencode_agents(home:Path,root:Path)->dict:
    """Install the Orchestrator and Sentinel role profiles next to the other LHC agents."""
    target=home/".config/opencode/agents"
    done={}
    for name,description in OPENCODE_ROLES.items():
        src=next((c/f"{name}.md" for c in (root/"common/agents",root/"src/common/agents") if (c/f"{name}.md").is_file()),None)
        if src is None:
            continue
        payload=f"---\ndescription: {description}\nmode: primary\n---\n\n"+src.read_text(encoding="utf-8")
        file=target/f"{name.lower()}.md"
        if not file.is_file() or file.read_text(encoding="utf-8")!=payload:
            target.mkdir(parents=True,exist_ok=True)
            file.write_text(payload,encoding="utf-8")
        done[name]=str(file)
    return {"agents":done}

def register_opencode_plugin(home:Path,root:Path,plugin_dir:Path)->dict:
    """Install the LHC OpenCode plugin so OpenCode auto-discovers it.

    OpenCode scans `<config>/plugin/*.ts` and `<config>/plugins/*.ts` and
    instantiates every export of each file, so only the plugin entry file is
    installed here. The package root is recorded next to the LHC state so the
    installed plugin can find the current AGENTS.md and the Python guard.
    """
    source=root/"opencode"
    if not source.is_dir():
        raise ValueError("The installed package has no opencode plugin directory")
    plugin_dir=plugin_dir.expanduser().resolve()
    plugin_dir.mkdir(parents=True,exist_ok=True)
    installed={}
    for name in OPENCODE_PLUGIN_FILES:
        src=source/name
        if not src.is_file():
            raise ValueError(f"The installed package is missing the OpenCode plugin file: {name}")
        target=plugin_dir/name
        payload=src.read_text(encoding="utf-8")
        if not target.exists() or target.read_text(encoding="utf-8")!=payload:
            if target.exists():
                backup=backup_path(home,"opencode","-"+name)
                backup.parent.mkdir(parents=True,exist_ok=True)
                backup.write_text(target.read_text(encoding="utf-8"),encoding="utf-8")
            target.write_text(payload,encoding="utf-8")
        installed[name]=str(target)
    state=home/".local/state/last-human-commit/opencode.json"
    state.parent.mkdir(parents=True,exist_ok=True)
    state.write_text(json.dumps({
        "packageRoot":str(root),
        "pluginDir":str(plugin_dir),
        "pluginFiles":installed,
        "registeredAt":datetime.now(timezone.utc).isoformat(),
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    extra={}
    if plugin_dir.parent==(home/".config/opencode").resolve():
        extra.update(register_opencode_mcp(home,root));extra.update(register_opencode_agents(home,root))
    return {"dir":str(plugin_dir),"files":installed,"state":str(state),**extra}

def configure(home:Path,root:Path,runtime:str,replace_gsd:bool=False,opencode_plugin_dir:Path|None=None)->dict:
    home=home.expanduser().resolve();root=root.expanduser().resolve()
    if not (root/"AGENTS.md").is_file() or not (root/"skills/last-human-commit/SKILL.md").is_file():
        raise ValueError("Select an installed package with its router and skills")
    destinations={"codex":".codex/AGENTS.md","claude":".claude/CLAUDE.md","opencode":".config/opencode/AGENTS.md"}
    plugin_dir=(opencode_plugin_dir or home/".config/opencode/plugin").expanduser().resolve()
    file=home/destinations[runtime]
    before=file.read_text() if file.exists() else ""
    text=before
    markers=[("lhc-autoentry","lhc-autoentry"),("last-human-commit","last-human-commit")]
    if replace_gsd:markers.append(("ogsd-autoentry","ogsd-autoentry"))
    for start,end in markers:
        pattern=re.compile(r"<!-- "+re.escape(start)+r":begin -->.*?<!-- "+re.escape(end)+r":end -->\s*",re.S)
        text=pattern.sub("",text)
    pointer=f"{BEGIN}\nFor an engineering request, automatically read `{root/'AGENTS.md'}` once and use English for planning/new records/agent coordination and the user's language for user answers. Preserve original user data. No LHC command is required. Resume the same task after compaction. This LHC router is the default; other workflow skills are optional methods.\n{END}\n"
    if runtime == "codex":
        pointer = (f"{BEGIN}\nLHC is the default for engineering requests; no explicit plugin mention is needed. "
            "The native LHC hook supplies the current absolute AGENTS.md and tool paths; use that root, "
            "not a cached version from an earlier thread. Before coding, state the tangible before/after "
            "result; choose working solution → ideal → useful 80%; for bugs use RED → fix → GREEN. "
            "Keep mandatory hourly direction and 120-minute learning reviews; fresh Zero Knowledge "
            "feedback belongs to major milestones, not every edit. If native LHC context is absent, "
            "report the missing runtime rather than treating an AGENTS read as activation. Use English for new internal records/coordination; answer the user in their language, preserving original user data.\n"
            f"{END}\n")
    elif runtime == "opencode":
        # The native OpenCode plugin injects the current installed AGENTS.md and
        # reports time-only reminders. It does not review, gate or approve work.
        # No package path is written here: the plugin resolves the current
        # installed root at dispatch, and a pinned path would drift.
        pointer = (f"{BEGIN}\n"
            "LHC is active in native OpenCode engineering sessions through the installed "
            "LHC plugin. The plugin injects the current installed AGENTS.md into the system "
            "context and reports time-only reminders at tool and idle boundaries; after "
            "compaction it re-injects the AGENTS.md pointer and the bounded current-handoff.md "
            "pointer. The plugin does not review, gate, approve or evaluate a diff. "
            "The core workflow stays yours: TDD RED/GREEN, working→ideal→useful-80%, "
            "review→delivery that fixes known receipt metadata from Git/CI instead of hiring "
            "a new reviewer, hourly direction and 120-minute learning checks, and independent "
            "Zero Knowledge only at major milestones. If the plugin context is missing, say "
            "activation is unverified. Use English for internal records/coordination and the "
            "user's language for answers; preserve original user data.\n"
            f"{END}\n")
    after=text.rstrip()+"\n\n"+pointer
    result={"path":str(file),"root":str(root)}
    if before==after:
        result["changed"]=False
    else:
        backup=backup_path(home,runtime)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if file.exists():backup.write_text(before,encoding="utf-8")
        file.parent.mkdir(parents=True,exist_ok=True)
        temporary=file.with_name(file.name+".lhc-"+uuid.uuid4().hex)
        try:
            temporary.write_text(after,encoding="utf-8")
            os.replace(temporary,file)
        finally:temporary.unlink(missing_ok=True)
        result["changed"]=True
        result["backup"]=str(backup) if before else None
    if runtime=="opencode":
        result["plugin"]=register_opencode_plugin(home,root,plugin_dir)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',choices=('codex','claude','opencode'),required=True)
    parser.add_argument('--plugin-root',type=Path,required=True)
    parser.add_argument('--home',type=Path,default=Path.home())
    parser.add_argument('--replace-gsd-entry',action='store_true')
    parser.add_argument('--opencode-plugin-dir',type=Path,default=None,
        help="OpenCode plugin directory; defaults to <home>/.config/opencode/plugin. "
             "Use <project>/.opencode/plugin for a project-local install.")
    args=parser.parse_args()
    try:print(json.dumps(configure(args.home,args.plugin_root,args.runtime,args.replace_gsd_entry,args.opencode_plugin_dir),ensure_ascii=False))
    except (OSError,ValueError) as error:parser.exit(2,str(error)+'\n')
if __name__=='__main__':main()
