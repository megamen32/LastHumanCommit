L06 corrected candidate: PASS

Candidate d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487. Exact package matches candidate (git diff empty). Same bounded public CLI/MCP lifecycle journey, all 12 checks PASS, exit 0. Prior FAIL evidence preserved unchanged.

B15: show_plan now separates Saved queue from dispatchable none, shows admission L02=assignment_running and execution assignment=running/runtime=running/wake=waiting. No unconditional Next L02. L01 shows accepted/completed/resumed.

Files: reproducer-final.py, acceptance-final.json, observations-final.json, mcp-tools-list-final.json, package-receipt-final.json. Only own HTTP MCP fixture, no real native turn/delivery/resume, no shared runtime writes. Source implementation and author tests not read. Real LLM execution and physical continuation delivery remain unproven by design. Release/merge/canonical worker_finish belong to root.
