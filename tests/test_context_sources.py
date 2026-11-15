# LHC:COVERS src/common/tools/lhc_context_sources.py src/common/tools/lhc_plan_mcp.py
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_plan_mcp as mcp

class ContextSourcesTests(unittest.TestCase):
    def test_resources_are_advertised_without_removing_tools(self):
        init = mcp.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}})
        self.assertIn('resources', init['result']['capabilities'])
        result = mcp.handle({'jsonrpc':'2.0','id':2,'method':'resources/list','params':{}})
        entries = result['result']['resources']
        self.assertGreaterEqual(len(entries), 5)
        self.assertEqual(len({e['uri'] for e in entries}), len(entries))
        for entry in entries:
            self.assertEqual(entry['_meta']['io.gptadmin/context-source']['schema_version'], 1)
        self.assertIn('list_models', [t['name'] for t in mcp.TOOLS])

    def test_every_resource_reads_exact_current_text_and_digest(self):
        listed = mcp.handle({'jsonrpc':'2.0','id':1,'method':'resources/list'})['result']['resources']
        for resource in listed:
            read = mcp.handle({'jsonrpc':'2.0','id':2,'method':'resources/read','params':{'uri':resource['uri']}})
            data = read['result']['contents'][0]
            self.assertEqual(data['uri'], resource['uri'])
            self.assertEqual(hashlib.sha256(data['text'].encode()).hexdigest(), resource['_meta']['io.gptadmin/context-source']['sha256'])
            self.assertEqual(len(data['text'].encode()), resource['size'])

    def test_arbitrary_files_and_traversal_are_not_resources(self):
        for uri in ['file:///etc/passwd','lhc://context/../../etc/passwd','lhc://context/workflow?x=1','lhc://context/absent']:
            result = mcp.handle({'jsonrpc':'2.0','id':1,'method':'resources/read','params':{'uri':uri}})
            self.assertEqual(result['error']['code'], -32602)

    def test_real_stdio_resource_flow(self):
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},{'jsonrpc':'2.0','id':2,'method':'resources/list'},{'jsonrpc':'2.0','id':3,'method':'resources/read','params':{'uri':'lhc://context/workflow'}}]
        result=subprocess.run([sys.executable,str(ROOT/'plugins/last-human-commit/scripts/plan_mcp.py')],input=''.join(json.dumps(x)+'\n' for x in messages),capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        replies=[json.loads(x) for x in result.stdout.splitlines()]
        self.assertIn('Last Human Commit', replies[-1]['result']['contents'][0]['text'])

if __name__ == '__main__': unittest.main()
