import json,os,pathlib,shutil,subprocess,sys,tempfile
repo=pathlib.Path(sys.argv[1])
with tempfile.TemporaryDirectory(prefix='lhc-projection-') as temp:
    root=pathlib.Path(temp)
    package=root/'package'
    shutil.copytree(repo/'plugins/last-human-commit/native/codex',package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    plan=root/'plan'
    plan.mkdir()
    fields={'label':'Isolated package probe','kind':'task','status':'queued','estimate_minutes':1,'description':'Synthetic release consumer','acceptance':'Canonical create command succeeds'}
    env=os.environ.copy()
    for key in ('CODEX_THREAD_ID','LHC_MCP_ACTOR_CONTEXT','OPENCODE_SESSION_ID','ZCODE_SESSION_ID'):
        env.pop(key,None)
    argv=[sys.executable,str(package/'tools/lhc_plan_json.py'),'create-leaf',str(plan),'T1','--fields',json.dumps(fields)]
    result=subprocess.run(argv,cwd=root,env=env,text=True,capture_output=True,timeout=30)
    print('COMMAND: python3 isolated-package/tools/lhc_plan_json.py create-leaf isolated-plan T1 --fields <synthetic>')
    print('RETURN_CODE:',result.returncode)
    print(result.stdout,end='')
    print(result.stderr,end='')
    if result.returncode:
        print('FAIL: isolated native package CLI create-leaf')
        raise SystemExit(1)
    saved=json.loads((plan/'leaves/T1.json').read_text())
    assert saved['status']=='queued'
    print('PASS: isolated native package CLI create-leaf')
