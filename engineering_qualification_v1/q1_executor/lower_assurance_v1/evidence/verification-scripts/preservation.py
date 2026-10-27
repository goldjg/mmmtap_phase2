"""Reuse prior read-only preservation checks; never execute old campaigns."""
from pathlib import Path
import subprocess
from engineering_qualification_v1.q1_executor import engine
from engineering_qualification_v1.q1_executor.model import encode,decode,raw_hash
from engineering_qualification_v1.q1_executor.transport_qualification import snapshot
root=Path.cwd();pkg=root/'engineering_qualification_v1/q1_executor';out=pkg/'lower_assurance_v1/evidence'
prior=decode((pkg/'live_campaign_v1/evidence/preservation.json').read_bytes())
baseline='0e35fb9a0da32e8ed066ed10421bfa9c5d2060bb'
results={}
seals=dict(prior['historical_seals'])
seals['engineering_qualification_v1/q1_executor/live_campaign_v1/SHA256SUMS.v1.txt']={}
for relative,old in seals.items():
 seal=root/relative
 if old:assert raw_hash(seal.read_bytes())==old['seal_sha256']
 base=root if any(x in relative for x in ('systemone_typed_v1/','systemone_https_v1/','live_campaign_v1/')) else pkg if 'q1_executor/' in relative else seal.parent
 count=0;historical=[]
 for line in seal.read_text().splitlines():
  expected,name=line.split('  ',1);path=base/name;rel=path.relative_to(root).as_posix();count+=1
  if raw_hash(path.read_bytes())==expected:continue
  revisions=[baseline]+[a['producer'] for a in old.get('historical_producer_bytes',[]) if a['path']==rel and a['sha256']==expected]
  revisions+=subprocess.check_output(['git','log','--format=%H',baseline,'--',rel],text=True).splitlines()
  for revision in dict.fromkeys(revisions):
   r=subprocess.run(['git','show',revision+':'+rel],capture_output=True)
   if r.returncode==0 and raw_hash(r.stdout)==expected:
    historical.append({'path':rel,'sha256':expected,'producer':revision});break
  else:raise AssertionError(('unresolved_historical_producer',rel))
 results[relative]={'seal_sha256':raw_hash(seal.read_bytes()),'verified_entries':count,'historical_producer_bytes':historical}
campaigns={}
paths=dict(prior['campaigns_reconstructed_readonly'])
paths['engineering_qualification_v1/q1_executor/live_campaign_v1/evidence/qualified-full-campaign/campaign']={}
for relative,old in paths.items():
 p=root/relative;before=snapshot(p);r=engine.verify(p);assert before==snapshot(p)
 if old:assert r['summary']['evidence_tip_sha256']==old['evidence_tip_sha256']
 campaigns[relative]={'verification':'PASS','positions':r['summary']['scheduled_positions'],'evidence_tip_sha256':r['summary']['evidence_tip_sha256'],'files_unchanged':True}
unchanged={}
for rel,expected in prior['unchanged_worker_instruments_topology'].items():
 assert raw_hash((root/rel).read_bytes())==expected;unchanged[rel]=expected
original=decode(Path('/tmp/q1-lower-original.stdout').read_bytes())
assert original['preservation']['original_entries_verified']==40538
assert original['preservation']['changed_or_missing']==[]
r={'baseline':baseline,'historical_seals':results,'campaigns_reconstructed_readonly':campaigns,'unchanged_worker_instruments_topology':unchanged,'original_custody':original,'real_provider_calls':0}
(out/'preservation.json').write_bytes(encode(r))
print(encode({'historical_seals':len(results),'sealed_entries':sum(a['verified_entries'] for a in results.values()),'campaigns_readonly':len(campaigns),'original_custody':40538}).decode())
