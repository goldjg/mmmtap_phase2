from pathlib import Path
import hashlib,json,subprocess,sys
from engineering_qualification_v1.q1_executor import engine
from engineering_qualification_v1.q1_executor.model import encode,decode,raw_hash
from engineering_qualification_v1.q1_executor.transport_qualification import snapshot
root=Path.cwd();pkg=root/'engineering_qualification_v1/q1_executor';out=pkg/'live_campaign_v1/evidence'
prior=decode((pkg/'systemone_https_v1/jevkey_evidence/preservation.json').read_bytes())
results={}
for relative,old in prior['historical_seals'].items():
 seal=root/relative
 assert raw_hash(seal.read_bytes())==old['seal_file_sha256']
 base=root if 'systemone_typed_v1/' in relative or 'systemone_https_v1/' in relative else pkg if 'q1_executor/' in relative else seal.parent
 entries=[]
 for line in seal.read_text().splitlines():
  expected,name=line.split('  ',1);path=base/name;rel=path.relative_to(root).as_posix();where='current'
  if raw_hash(path.read_bytes())!=expected:
   candidates=['54b8762ecdc48b96ebd3ae5f394b995c89cc9094']+[a['historical_revision'] for a in old['historical_producer_bytes'] if a['path']==rel and a['sha256']==expected]
   for rev in candidates:
    r=subprocess.run(['git','show',rev+':'+rel],capture_output=True,env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'})
    if r.returncode==0 and raw_hash(r.stdout)==expected:where=rev;break
   else:raise AssertionError(('seal_unresolved',rel))
  entries.append({'path':rel,'sha256':expected,'producer':where})
 results[relative]={'seal_sha256':raw_hash(seal.read_bytes()),'verified_entries':len(entries),'historical_producer_bytes':[a for a in entries if a['producer']!='current']}
seal=pkg/'systemone_https_v1/SHA256SUMS.jevkey.v1.txt';n=0;historic=[]
for line in seal.read_text().splitlines():
 expected,rel=line.split('  ',1);n+=1
 if raw_hash((root/rel).read_bytes())!=expected:
  raw=subprocess.check_output(['git','show','54b8762ecdc48b96ebd3ae5f394b995c89cc9094:'+rel],env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'})
  assert raw_hash(raw)==expected,rel;historic.append(rel)
results[str(seal.relative_to(root))]={'seal_sha256':raw_hash(seal.read_bytes()),'verified_entries':n,'producer_baseline_for_changed_files':historic}
campaigns={}
for rel,old in prior['campaigns_readonly'].items():
 p=root/rel;before=snapshot(p);r=engine.verify(p);assert before==snapshot(p)
 assert r['summary']['evidence_tip_sha256']==old['evidence_tip_sha256']
 campaigns[rel]={'verification':'PASS','positions':r['summary']['scheduled_positions'],'evidence_tip_sha256':r['summary']['evidence_tip_sha256'],'files_unchanged':True}
unchanged={}
for rel in ['engineering_qualification_v1/q1_executor/broker_v1/worker.py','engineering_qualification_v1/q1_executor/transport_bootstrap.py','engineering_qualification_v1/q1_executor/full_matrix.py','engineering_qualification_v1/q1_executor/systemone_typed_v1/contract.py','phase2_v2/instrument.py','phase2_v2/continuation.py']:
 raw=subprocess.check_output(['git','show','54b8762ecdc48b96ebd3ae5f394b995c89cc9094:'+rel],env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'});assert raw==(root/rel).read_bytes();unchanged[rel]=raw_hash(raw)
original=decode(Path('/tmp/q1-final-original-custody.stdout').read_bytes());assert original['preservation']['original_entries_verified']==40538
r={'baseline':'54b8762ecdc48b96ebd3ae5f394b995c89cc9094','historical_seals':results,'campaigns_reconstructed_readonly':campaigns,'unchanged_worker_instruments_topology':unchanged,'original_custody':original,'historical_access_not_reclassified':True,'real_provider_calls':0}
(out/'preservation.json').write_bytes(encode(r));print(encode({'historical_seals':len(results),'sealed_entries':sum(a['verified_entries'] for a in results.values()),'campaigns_readonly':len(campaigns),'original_custody':40538}).decode())
