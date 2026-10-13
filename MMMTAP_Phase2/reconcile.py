#!/usr/bin/env python3
"""MMMTAP Phase 2 read-only archive and primary corpus reconciliation."""
import argparse,csv,hashlib,json,os,zipfile,collections
from pathlib import Path

def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def dump_csv(path,rows,fields):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def discover(roots):
 found=[];seen=set()
 ignore={'.git','node_modules','.venv','venv','__pycache__','.cache','.npm','.cargo','.rustup','.local','.config','.vscode','site-packages'}
 for root in roots:
  if not root.exists():continue
  for dp,dirs,files in os.walk(root,followlinks=False):
   dirs[:]=[d for d in dirs if d not in ignore and not d.startswith('.')]
   for f in files:
    if not f.lower().endswith('.zip'):continue
    p=Path(dp)/f
    try: identity=(p.stat().st_dev,p.stat().st_ino)
    except OSError:continue
    if identity in seen:continue
    seen.add(identity);found.append(p)
 return sorted(found)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--plan-dir',type=Path,required=True)
 p.add_argument('--corpus-zip',type=Path,required=True)
 p.add_argument('--search-root',type=Path,action='append',required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((a.plan_dir/'corpus_manifest.json').read_text())
 inventory=json.loads((a.plan_dir/'legacy_inventory.json').read_text())
 actual=sha_file(a.corpus_zip)
 if actual!=manifest['archive_sha256']:raise SystemExit('FATAL: primary ZIP hash mismatch: '+actual)
 items=manifest['items'];case_ids=set();variants=set();issues=[];members=[]
 with zipfile.ZipFile(a.corpus_zip) as z:
  corrupt=z.testzip()
  if corrupt:raise SystemExit('FATAL: primary ZIP CRC failure: '+corrupt)
  for item in items:
   m=item['input_member'];case_ids.add(item['case_id']);variants.add(item['variant_id'])
   try:content=z.read(m)
   except KeyError:issues.append('Missing corpus member '+m);continue
   digest=hashlib.sha256(content).hexdigest()
   if digest!=item['input_sha256']:issues.append('Hash mismatch '+m)
   if len(content)!=item['bytes']:issues.append('Size mismatch '+m)
   members.append({'case_id':item['case_id'],'variant_id':item['variant_id'],'input_member':m,'sha256':digest,'bytes':len(content),'verified':digest==item['input_sha256'] and len(content)==item['bytes']})
 if len(items)!=manifest['n_inputs'] or len(case_ids)!=manifest['n_cases'] or len(variants)!=manifest['n_variants']:
  issues.append('Manifest declared dimensions do not match item enumeration')
 primary_ok=not issues
 # Archive registry: by hash, never by mutable/display filename alone.
 found=discover(a.search_root)
 found_records=[];by_hash=collections.defaultdict(list);by_basename=collections.defaultdict(list)
 for f in found:
  try:h=sha_file(f);zi=zipfile.ZipFile(f);names=zi.namelist();zi.close()
  except (OSError,zipfile.BadZipFile) as e:
   found_records.append({'path':str(f),'filename':f.name,'sha256':'','zip_members':0,'scan_status':f'error:{type(e).__name__}' });continue
  rec={'path':str(f),'filename':f.name,'sha256':h,'zip_members':len(names),'scan_status':'index_ok'}
  found_records.append(rec);by_hash[h].append(rec);by_basename[f.name].append(rec)
 # Exact SHA overrides missing/renamed basenames; identify differing names with matching hash.
 registry=[]
 for entry in inventory['archives']:
  matches=by_hash.get(entry['sha256'],[])
  names=by_basename.get(entry['archive'],[])
  status='exact_sha_match' if matches else 'same_name_different_sha' if names else 'not_located'
  registry.append({'inventory_name':entry['archive'],'expected_sha256':entry['sha256'],
   'status':status,'matched_paths':' | '.join(x['path'] for x in matches),
   'same_name_paths':' | '.join(x['path'] for x in names) if not matches else '',
   'recorded_entries':entry.get('entries'),'candidate_case_status':'unclassified_requires_case_level_review'})
 # Candidate archive member index for manual eligibility/overlap work, no source extraction/execution.
 details=[]
 referenced_hashes=set(e['sha256'] for e in inventory['archives'])
 for rec in found_records:
  if rec['sha256'] not in referenced_hashes:continue
  with zipfile.ZipFile(rec['path']) as z:
   for info in z.infolist():
    if info.is_dir():continue
    details.append({'archive_sha256':rec['sha256'],'archive_path':rec['path'],
      'member':info.filename,'size':info.file_size,'crc32':f'{info.CRC:08x}',
      'classification':'unclassified'})
 dump_csv(a.out/'primary_inputs.csv',members,['case_id','variant_id','input_member','sha256','bytes','verified'])
 dump_csv(a.out/'archive_registry.csv',registry,['inventory_name','expected_sha256','status','matched_paths','same_name_paths','recorded_entries','candidate_case_status'])
 dump_csv(a.out/'archive_members.csv',details,['archive_sha256','archive_path','member','size','crc32','classification'])
 dump_csv(a.out/'discovered_zips.csv',found_records,['path','filename','sha256','zip_members','scan_status'])
 summary={'protocol':'MMMTAP-P2-RECONCILE-v1','execution':'read_only_no_model_calls','primary_archive_sha256':actual,
 'primary_verified':primary_ok,'primary_issues':issues,'primary_items':len(members),'cases':len(case_ids),'variants':len(variants),
 'inventory_records':len(registry),'inventory_exact_sha_matches':sum(r['status']=='exact_sha_match' for r in registry),
 'inventory_same_name_different_sha':sum(r['status']=='same_name_different_sha' for r in registry),
 'inventory_not_located':sum(r['status']=='not_located' for r in registry),'discovered_zips':len(found_records),
 'archive_member_index_rows':len(details), 'historical_unique_cases':'NOT_YET_CLASSIFIED',
 'no_historical_auto_admission':True}
 (a.out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
 (a.out/'SHA256SUMS.txt').write_text(''.join(sha_file(x)+'  '+x.name+'\n' for x in sorted(a.out.iterdir()) if x.name!='SHA256SUMS.txt'))
 print(json.dumps(summary,indent=2))
 if not primary_ok:raise SystemExit('FATAL: primary corpus failed content verification; see SUMMARY.json')

if __name__=='__main__':main()
