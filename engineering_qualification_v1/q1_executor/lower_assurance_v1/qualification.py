"""Focused candidate run: new CLI execution/profile/labels, existing S1 TLS peer.

One complete run is necessary because all generator execution bindings and all
153 receipt labels changed. Reuse the prior transport/network qualification;
do not repeat its broad destination/error matrix or any live inference.
"""
from collections import Counter
import base64
import copy
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys

from .contract import build, validate_manifest
from . import VERSION, DESIGNATION
from .. import engine
from ..model import encode, decode, digest, raw_hash
from ..systemone_https_v1 import DESTINATION
from ..systemone_https_v1.qualification import certificate, wait_port, assert_rejected
from ..systemone_https_v1.jevkey_qualification import setup_peer, command, assert_no_dummy_in_custody
from ..systemone_https_v1.egress import install_fixture_policy
from ..transport_qualification import snapshot

MODULE='engineering_qualification_v1.q1_executor'
FAULTS={
    'c01-gemini-r1-c1-g1':'cli_tools', 'c01-haiku-r1-c2-g1':'invalid_assessment',
    'c01-sol-r1-c3-g1':'cli_timeout','c02-gemini-r1-e1-s1':'identity_unknown',
    'c02-haiku-r1-e3-cn-s2':'identity_mismatch','c02-sol-r1-e3-nc-g1':'cli_interrupt',
    'c03-gemini-r1-c1-g1':'cli_credential_echo','c03-haiku-r1-c1-g1':'cli_model'}


def run(root):
    if 'JEVKEY' in os.environ or 'COPILOT_GITHUB_TOKEN' in os.environ:
        raise ValueError('offline_qualifier_must_not_inherit_operator_credentials')
    root.mkdir(mode=0o700);peer,prefix=setup_peer();command(['/usr/sbin/ip','link','set','lo','up'])
    cert,key=certificate(root,'local-peer',DESTINATION['host'])
    dummy='PUBLIC-DUMMY-JEV-'+secrets.token_hex(12)
    rd,wr=os.pipe2(os.O_CLOEXEC);os.write(wr,dummy.encode());os.close(wr)
    log=(root/'server.stderr').open('wb')
    server=subprocess.Popen(prefix+[sys.executable,'-B','-m',MODULE+'.live_campaign_v1.fixture','--root',str(root),
        '--cert',str(cert),'--key',str(key),'--expected-dummy-fd',str(rd)],pass_fds=(rd,),
        env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin'},stdout=subprocess.DEVNULL,stderr=log)
    os.close(rd)
    try:
        port=wait_port(root,server)
        route={'address':'192.0.2.2','port':port,'ca_pem':cert.read_text(),'ca_sha256':raw_hash(cert.read_bytes()),
            'network_namespace':os.readlink('/proc/self/ns/net'),'interfaces':['lo','q1-client']}
        install_fixture_policy(port,route['address'])
        manifest=build(root/'packets',fixture_route=route,scenarios=FAULTS)
        campaign=engine.create(root/'campaign',root/'packets')
        argv=[sys.executable,'-B','-m',MODULE,'resume','--campaign',str(campaign),'--offline-subprocess']
        env={'LANG':'C.UTF-8','PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','JEVKEY':dummy}
        first=subprocess.run(argv,env=env,capture_output=True)
        (root/'first.stdout').write_bytes(first.stdout);(root/'first.stderr').write_bytes(first.stderr)
        assert first.returncode==75,first.stderr.decode()[-2000:]
        second=subprocess.run(argv,env=env,capture_output=True)
        (root/'recovery.stdout').write_bytes(second.stdout);(root/'recovery.stderr').write_bytes(second.stderr)
        assert second.returncode==0,second.stderr.decode()[-2000:]
        report=engine.verify(campaign);saved=report['receipts'];assert len(saved)==153
        before=snapshot(campaign);third=subprocess.run(argv,env=env,capture_output=True)
        assert third.returncode==0 and snapshot(campaign)==before
        assert saved['c02-sol-r1-e3-nc-g1']['state']=='interrupted'
        assert saved['c01-haiku-r1-c2-g1']['state']=='invalid'
        assert saved['c01-sol-r1-c3-g1']['state']=='unavailable'
        for receipt in saved.values():
            assert receipt['assurance']['designation']==DESIGNATION
            assert receipt['assurance_sha256']==digest(manifest['assurance']) and not receipt['strict_scientific_pooling_permitted']
        db=engine.connect(campaign,readonly=True)
        try:
            rows=[(ident,decode(record)) for ident,record in db.execute('SELECT id,record FROM transports') if record]
            cli=[(i,r) for i,r in rows if 'cli' in r]
            assert len(cli)>80 and all(r['cli']['top_level_CLI_launches']==1 for _,r in cli)
            assert all(r['cli']['serving_identity_attestation'] is None and r['cli']['provider_HTTP_attempts']=='UNKNOWN' for _,r in cli)
            assert all(r['cleanup'] for _,r in cli)
            probes=[]
            for ident,r in cli:
                for line in base64.b64decode(r['stderr_b64']).splitlines():
                    if line.startswith(b'Q1_CLI_PROBE '):
                        data=decode(line[len(b'Q1_CLI_PROBE '):]);assert all(data.values());probes.append({'position':ident,**data})
            assert len(probes)>80
            sol=[r for i,r in cli if '-sol-' in i and r['status']=='completed'];assert sol
            assert all(r['cli']['client_reported_model'] is None and r['observed_identity'] is None for r in sol)
            assert any(r['cli']['credential_capture_refused'] for _,r in cli)
            assert all('https' not in r for _,r in cli)
            launches=Counter(next(p['route'] for p in manifest['positions'] if p['id']==i) for i,_ in cli)
        finally:db.close()
        posts=[decode(line) for line in (root/'posts.jsonl').read_bytes().splitlines()]
        assert len({p['position'] for p in posts})==len(posts)
        assert set(p['route'] for p in posts)=={'native','carl'}
        assert (root/'server.stderr').read_bytes()==b''
        assert_no_dummy_in_custody(root,dummy)
        assert_no_dummy_in_custody(root,'PUBLIC-DUMMY-SUBSCRIPTION-CREDENTIAL')
        negatives=negative_checks(root,campaign,manifest)
        result={'version':VERSION,'designation':DESIGNATION,'scheduled_positions':153,'scheduled_generators':99,'scheduled_specialists':54,
            'summary':report['summary'],'outcomes':dict(Counter(r['state'] for r in saved.values())),
            'actual_contained_CLI_event_fixture_processes':len(cli),'CLI_launches_by_route':dict(launches),
            'actual_generator_CLI_inference_processes':0,'actual_local_SystemOne_POSTs':len(posts),
            'SystemOne_POSTs_by_presentation':dict(Counter(p['route'] for p in posts)),
            'one_launch_per_reserved_generator_attempt':True,'no_retransmission_after_interruption':True,
            'repeat_resume_database_unchanged':True,'CLI_streams_not_provider_HTTP':True,
            'all_receipts_permanently_lower_assurance':True,'serving_identity_unavailable':True,
            'credential_non_disclosure':True,'actual_CLI_containment_probes':probes,'negative_checks':negatives,
            'SystemOne_transport_regressions_reused_from_baseline':'0e35fb9a0da32e8ed066ed10421bfa9c5d2060bb',
            'real_provider_calls':0,'launch_approval':'NOT APPROVED'}
        (root/'acceptance.json').write_bytes(encode(result));return result
    finally:
        server.terminate();server.wait(timeout=5);log.close();peer.terminate();peer.wait(timeout=5)
        for stream in (peer.stdin,peer.stdout):stream.close()
        key.unlink(missing_ok=True)


def negative_checks(root,campaign,m):
    checks={}
    for name,mutate in [('assurance_relabel',lambda x:x['assurance'].update(designation='STRICT_SCIENTIFIC_QUALIFICATION')),
                        ('launch_toggle',lambda x:x['launch_candidate'].update(launch_approval='APPROVED')),
                        ('model_substitution',lambda x:x['production_campaign']['routes']['sol'].update(model='substitute')),
                        ('duplicate_position',lambda x:x['positions'].append(copy.deepcopy(x['positions'][0])))]:
        candidate=copy.deepcopy(m);mutate(candidate)
        candidate['manifest_sha256']=digest({k:v for k,v in candidate.items() if k!='manifest_sha256'})
        checks[name]=assert_rejected(lambda:validate_manifest(root/'packets',candidate,encode(candidate)))
    for name,sql in [('receipt_relabel',"UPDATE receipts SET body=x'7b7d' WHERE id=(SELECT id FROM receipts LIMIT 1)"),
                     ('CLI_stdout_tamper',"UPDATE responses SET raw=x'74616d706572' WHERE id=(SELECT id FROM responses LIMIT 1)"),
                     ('request_tamper',"UPDATE attempts SET request=x'7b7d' WHERE id=(SELECT id FROM attempts LIMIT 1)")]:
        target=root/('tampered-'+name);shutil.copytree(campaign,target)
        db=sqlite3.connect(target/'campaign.sqlite3');db.execute(sql);db.commit();db.close()
        checks[name]=assert_rejected(lambda:engine.verify(target))
        # Keep negative copies: never mutate/relabel original first attempts.
    checks['copied_custody_cannot_resume']=assert_rejected(lambda:engine.resume(root/'tampered-request_tamper',offline_subprocess=True))
    return checks
