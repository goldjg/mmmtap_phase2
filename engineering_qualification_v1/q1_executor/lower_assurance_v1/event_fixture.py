"""Pinned non-inference event producer inside the actual CLI containment profile."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

req=json.loads(Path('/inputs/request.json').read_bytes());scenario=Path('/inputs/scenario').read_text()
assert sys.stdin.buffer.read().decode()==req['instrument_request']['prompt']
checks={'JEVKEY_environment_absent':'JEVKEY' not in os.environ,'host_repo_hidden':not Path('/home/prometheus/git/mmmtap_phase2').exists(),
        'host_home_auth_hidden':not Path('/home/prometheus/.codex/auth.json').exists()}
for name,path in [('request_readonly','/inputs/request.json'),('work_readonly','/work/forbidden'),('usr_readonly','/usr/forbidden')]:
 try:Path(path).write_bytes(b'forbidden');checks[name]=False
 except OSError:checks[name]=True
lib=ctypes.CDLL(None,use_errno=True)
checks['namespace_change_denied']=lib.unshare(0x40000000)==-1 and ctypes.get_errno()==1
checks['internal_child_explicitly_permitted']=subprocess.run(['/usr/bin/true']).returncode==0
assert all(checks.values()),'containment_probe_failed'
os.write(2,b'Q1_CLI_PROBE '+json.dumps(checks,sort_keys=True).encode()+b'\n')
stdout=Path('/inputs/fixture.stdout').read_bytes();stderr=Path('/inputs/fixture.stderr').read_bytes()
if scenario=='cli_tools':stdout=b'{"type":"tool.execution_start"}\n'+stdout
if scenario=='cli_model':
 stdout=stdout.replace(req['instrument_request']['model'].encode(),b'unapproved-substitute')
if scenario=='cli_credential_echo':
 os.write(1,b'PUBLIC-DUMMY-SUBSCRIPTION-CREDENTIAL');raise SystemExit(0)
if scenario in ('cli_interrupt','cli_timeout'):
 os.write(1,stdout[:53]);time.sleep(3);raise SystemExit(0)
os.write(2,stderr)
os.write(1,stdout)
