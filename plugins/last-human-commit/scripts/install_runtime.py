#!/usr/bin/env python3
"""Point supported user instructions to a natively installed LHC package."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

BEGIN="<!-- lhc-autoentry:begin -->"
END="<!-- lhc-autoentry:end -->"
OPENCODE_PLUGIN_FILES=("lhc-v2.ts","lhc-boss-v2.ts")

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

OPENCODE_ROLES={"Lead":"LastHumanCommit Lead: owns classification, integration, proof, and release.",
                "Dispatcher":"LastHumanCommit Dispatcher: carries the owner's sessions to results from a registry and file mail; does not do the work.",
                "Sentinel":"LastHumanCommit Sentinel: watches one thing, reports only when something is wrong.",
                "Adviser":"LastHumanCommit Adviser: a second opinion on a hard decision.",
                "Critic":"LastHumanCommit Critic: finds where a plan or change breaks.",
                "Boss":"LastHumanCommit Boss: the last step before the owner.",
                "Reviewer":"LastHumanCommit Reviewer: reviews the integrated change once.",
                "Tester":"LastHumanCommit Tester: proves the claim on the real consumer path.",
                "Maintainer":"LastHumanCommit Maintainer: keeps the package and its installs current.",
                "Worker":"LastHumanCommit Worker: does one bounded leaf."}
OPENCODE_PRIMARY=("Lead","Dispatcher","Sentinel")

def register_opencode_agents(home:Path,root:Path)->dict:
    """Install every LHC role profile from the current package, replacing a stale copy.

    A profile left from an older package carries the rules of that package (the Lead of
    July asked the owner to choose between three plans), so a profile that differs is
    backed up and rewritten, not kept.
    """
    target=home/".config/opencode/agents"
    done={}
    for name,description in OPENCODE_ROLES.items():
        src=next((c/f"{name}.md" for c in (root/"common/agents",root/"src/common/agents") if (c/f"{name}.md").is_file()),None)
        if src is None:
            continue
        mode="primary" if name in OPENCODE_PRIMARY else "subagent"
        payload=f"---\ndescription: {description}\nmode: {mode}\n---\n\n"+src.read_text(encoding="utf-8")
        file=target/f"{name.lower()}.md"
        if not file.is_file() or file.read_text(encoding="utf-8")!=payload:
            target.mkdir(parents=True,exist_ok=True)
            if file.is_file():
                backup=backup_path(home,"opencode","-agent-"+name.lower())
                backup.parent.mkdir(parents=True,exist_ok=True)
                backup.write_text(file.read_text(encoding="utf-8"),encoding="utf-8")
            file.write_text(payload,encoding="utf-8")
        done[name]=str(file)
    return {"agents":done}

def register_opencode_skills(home:Path,root:Path)->dict:
    """Give OpenCode the LHC skills: one link per skill in its user skills folder.

    The link points at the installed package, so a package update is an update of the skill.
    A skill folder the owner made by hand under the same name is left alone.
    """
    source=root/"skills"
    if not source.is_dir():
        return {"skills":"skipped","reason":"the installed package has no skills folder"}
    target=home/".config/opencode/skills"
    done=[];kept=[]
    for skill in sorted(source.iterdir()):
        if not (skill/"SKILL.md").is_file():
            continue
        link=target/skill.name
        if link.is_symlink():
            if link.resolve()!=skill.resolve():
                link.unlink();link.symlink_to(skill.resolve())
            done.append(skill.name)
        elif link.exists():
            kept.append(skill.name)
        else:
            target.mkdir(parents=True,exist_ok=True)
            link.symlink_to(skill.resolve());done.append(skill.name)
    return {"skills":done,"skills_kept":kept}

def manifest_path(home:Path,runtime:str)->Path:
    return home/".local/state/last-human-commit"/f"install-manifest-{runtime}.json"

def digest(path:Path)->str:
    """sha256 of a file, or of the target text of a link (a link is what the installer wrote)."""
    data=os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    return hashlib.sha256(data).hexdigest()

def read_manifest(home:Path,runtime:str):
    try:
        data=json.loads(manifest_path(home,runtime).read_text(encoding="utf-8"))
    except (OSError,ValueError):
        return None
    rows=data.get("files") if isinstance(data,dict) else None
    return [r for r in rows if isinstance(r,dict) and isinstance(r.get("path"),str)] if isinstance(rows,list) else None

def is_lhc_agent(file:Path)->bool:
    """An agent file whose frontmatter names LastHumanCommit: written by an LHC installer, not by the owner."""
    try:
        text=file.read_text(encoding="utf-8")
    except (OSError,UnicodeDecodeError):
        return False
    if not text.startswith("---"):
        return False
    return "lasthumancommit" in text.split("---",2)[1].lower().replace(" ","")

def remove_with_backup(home:Path,runtime:str,path:Path)->None:
    """Keep a copy in the backup folder, then delete the file or the link itself."""
    backup=backup_path(home,runtime,"-removed-"+path.name)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():
        backup.write_text("symlink -> "+os.readlink(path)+"\n",encoding="utf-8")
    else:
        shutil.copy2(path,backup)
    path.unlink()

def prune_opencode(home:Path,root:Path,plugin_dir:Path,written:list)->dict:
    """Delete what an earlier install wrote and this one no longer does; never a foreign file.

    With a manifest from the previous install: its entries missing from the new one go (an entry the
    owner edited since is kept). Without one (the first install of this version): only the known list,
    the LHC orchestrator.md agent, dangling skill links into an LHC package and lhc-*.ts plugin files
    that are not part of this package. Each deleted file is copied to the backup folder first.
    """
    config=(home/".config/opencode")
    allowed=[config.resolve(),plugin_dir.resolve()]
    keep={str(Path(p)) for p in written}
    rows=[{"path":str(Path(p)),"sha256":digest(Path(p))} for p in sorted(keep) if os.path.lexists(p)]
    old=read_manifest(home,"opencode")
    removed=[];kept=[]
    def inside(path:Path)->bool:
        base=path.parent.resolve()/path.name
        return any(a==base.parent or a in base.parents for a in allowed)
    def drop(path:Path):
        if str(path) in keep or not os.path.lexists(path) or not inside(path):
            return
        remove_with_backup(home,"opencode",path);removed.append(str(path))
    if old is not None:
        for row in old:
            path=Path(row["path"])
            if str(path) in keep or not os.path.lexists(path):
                continue
            if not inside(path):
                continue
            if row.get("sha256") and digest(path)!=row["sha256"]:
                kept.append(str(path));continue
            drop(path)
    else:
        orchestrator=config/"agents/orchestrator.md"
        if orchestrator.is_file() and is_lhc_agent(orchestrator):
            drop(orchestrator)
        skills=config/"skills"
        if skills.is_dir():
            for link in sorted(skills.iterdir()):
                if link.is_symlink() and not link.exists():
                    target=os.readlink(link)
                    parts=[part.lower() for part in Path(target).parts]
                    # An LHC skill link points into the package (a last-human-commit folder, or
                    # <checkout>/skills/<name>); a path that merely passes a folder named
                    # LastHumanCommit on its way somewhere else is not ours.
                    ours=(Path(target).is_relative_to(root) or "last-human-commit" in parts
                          or (len(parts)>=3 and parts[-2]=="skills" and parts[-3] in {"lasthumancommit","last-human-commit"}))
                    if ours:
                        drop(link)
        for file in sorted(plugin_dir.glob("lhc-*.ts")):
            if file.name not in OPENCODE_PLUGIN_FILES:
                drop(file)
    manifest=manifest_path(home,"opencode")
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps({"runtime":"opencode","writtenAt":datetime.now(timezone.utc).isoformat(),"files":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"removed":removed,"kept_modified":kept,"manifest":str(manifest)}

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
        # OpenCode instantiates every plugin file, so a second copy doubles every hook:
        # an entry that already points at this source, or the long-standing
        # last-human-commit.ts, is the installed plugin and gets no sibling.
        existing=next((e for e in sorted(plugin_dir.glob("*.ts")) if e.resolve()==src.resolve()),None)
        if existing is None and (plugin_dir/"last-human-commit.ts").exists():
            existing=plugin_dir/"last-human-commit.ts"
        if existing is not None:
            if not existing.is_symlink() and existing.read_text(encoding="utf-8")!=src.read_text(encoding="utf-8"):
                existing.write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
            installed[name]=str(existing)
            continue
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
        extra.update(register_opencode_mcp(home,root));extra.update(register_opencode_agents(home,root));extra.update(register_opencode_skills(home,root))
        written=list(installed.values())+list((extra.get("agents") or {}).values())
        if isinstance(extra.get("skills"),list):
            written+=[str(home/".config/opencode/skills"/name) for name in extra["skills"]]
        extra.update(prune_opencode(home,root,plugin_dir,written))
    return {"dir":str(plugin_dir),"files":installed,"state":str(state),**extra}

def configure(home:Path,root:Path,runtime:str,replace_gsd:bool=False,opencode_plugin_dir:Path|None=None)->dict:
    home=home.expanduser().resolve();root=root.expanduser().resolve()
    if not (root/"AGENTS.md").is_file() or not (root/"skills/last-human-commit/SKILL.md").is_file():
        raise ValueError("Select an installed package with its router and skills")
    destinations={"codex":".codex/AGENTS.md","claude":".claude/CLAUDE.md","opencode":".config/opencode/AGENTS.md"}
    plugin_dir=(opencode_plugin_dir or home/".config/opencode/plugins").expanduser().resolve()
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
            "context, reports time facts at tool and idle boundaries, holds a stop (twice at most) "
            "while the session's plan has queued or running leaves, and re-injects the AGENTS.md "
            "pointer after compaction. It never reviews or approves a diff. The LHC role profiles "
            "(Lead, Dispatcher, Adviser, Critic, Worker and the rest) and skills (plan, plan-artifacts "
            "and the rest) are installed with it: type /plan to reconcile the "
            "work with the plan or to make one. Plan in stages, cut only the nearest stage into "
            "leaves of about 15 minutes, and choose yourself: the owner does not pick between plans. "
            "If the plugin context is missing, say activation is unverified. Use English for "
            "internal records/coordination and the user's language for answers; preserve original "
            "user data.\n"
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
    result["removed"]=[]
    if runtime=="opencode":
        result["plugin"]=register_opencode_plugin(home,root,plugin_dir)
        result["removed"]=result["plugin"].get("removed",[])
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
