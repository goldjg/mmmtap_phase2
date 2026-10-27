import hashlib,json,subprocess
from pathlib import Path
from engineering_qualification_v1.q1_executor import engine
from engineering_qualification_v1.q1_executor.model import PACKAGE,decode,digest,raw_hash
from engineering_qualification_v1.q1_executor.transport_qualification import snapshot
root=Path.cwd();base=PACKAGE
results={}
for seal in [base/'SHA256SUMS.txt',base/'SHA256SUMS.full-matrix.v1.txt',base/'SHA256SUMS.transport.v1.txt',base/'broker_v1/SHA256SUMS.v1.txt']:
 current=0;historic=[]
 for line in seal.read_text().splitlines():
  expected,name=line.split('  ',1);path=base/name
  if path.is_file() and raw_hash(path.read_bytes())==expected:
   current+=1;continue
  relative=path.relative_to(root).as_posix()
  commits=subprocess.check_output(['git','log','--format=%H','HEAD','--',relative],text=True).splitlines()
  found=None
  for commit in commits:
   raw=subprocess.run(['git','show',commit+':'+relative],capture_output=True)
   if raw.returncode==0 and raw_hash(raw.stdout)==expected:
    found=commit;break
  if found is None:raise AssertionError(('unresolved_historical_seal',str(seal),name))
  historic.append({'path':name,'sha256':expected,'historical_revision':found})
 results[seal.relative_to(root).as_posix()]={'entries':current+len(historic),'current_bytes_verified':current,'historical_source_bytes_verified':historic,'seal_sha256':raw_hash(seal.read_bytes())}
# These later packages are unchanged in their entirety, including all code.
for folder,name in [('engineering_qualification_v1/systemone_contract_resolution_v1','SHA256SUMS.txt'),('engineering_qualification_v1/provider_contract_qualification_v1','SHA256SUMS.txt'),('rd05_comparison/v1','SHA256SUMS.txt')]:
 seal=root/folder/name;count=0
 for line in seal.read_text().splitlines():
  expected,relative=line.split('  ',1)
  assert raw_hash((root/folder/relative).read_bytes())==expected,(folder,relative)
  count+=1
 results[str(seal.relative_to(root))]={'entries':count,'current_bytes_verified':count,'seal_sha256':raw_hash(seal.read_bytes())}
# Every old campaign is audited without writing lock files, sidecars or receipts.
paths=[base/'evidence/demo-campaign',base/'full_matrix_evidence/demonstration/normal-campaign',base/'full_matrix_evidence/demonstration/adverse-campaign',base/'transport_evidence/demonstration/campaign']
paths+=sorted(p.parent for p in (base/'broker_v1/evidence/qualification').glob('*/campaign/campaign.sqlite3'))
campaigns={}
for p in paths:
 before=snapshot(p);audit=engine.verify(p);assert before==snapshot(p)
 campaigns[p.relative_to(root).as_posix()]={'summary':audit['summary'],'files_unchanged':True}
changed=subprocess.check_output(['git','diff','--diff-filter=M','--name-only','9f375374c9daab1b6ae3a36e15593a340e65b9b7'],text=True).splitlines()
assert set(changed)=={'engineering_qualification_v1/q1_executor/engine.py','engineering_qualification_v1/q1_executor/model.py','engineering_qualification_v1/q1_executor/broker_v1/contract.py','engineering_qualification_v1/q1_executor/broker_v1/provider.py'},changed
print(json.dumps({'baseline':'9f375374c9daab1b6ae3a36e15593a340e65b9b7','historical_seals':results,'historical_campaigns_readonly':campaigns,'authorised_existing_code_changes':changed,'other_tracked_files_changed':False},indent=2))
