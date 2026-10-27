import base64
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from .contract import build, validate_manifest, assurance, rules, DESIGNATION
from . import profile
from .. import engine
from ..model import encode, decode, digest, raw_hash


class LowerAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='q1-lower-test-');self.root=Path(self.tmp.name)
        self.route={'address':'192.0.2.2','port':12345,'ca_pem':'offline','ca_sha256':raw_hash(b'offline'),
            'network_namespace':'net:[offline]','interfaces':['lo','q1-client']}

    def tearDown(self):self.tmp.cleanup()

    def test_frozen_candidate_graph_and_relabelling_denied(self):
        m=build(self.root/'packets')
        self.assertEqual(len(m['positions']),153)
        self.assertEqual(sum(p['kind']=='generator' for p in m['positions']),99)
        self.assertEqual(sum(len(p['dependencies']) for p in m['positions']),198)
        self.assertEqual(m['assurance']['designation'],DESIGNATION)
        for mutate in (lambda x:x['assurance'].update(designation='STRICT_SCIENTIFIC_QUALIFICATION'),
                       lambda x:x['launch_candidate'].update(launch_approval='APPROVED')):
            altered=copy.deepcopy(m);mutate(altered);altered['manifest_sha256']=digest({k:v for k,v in altered.items() if k!='manifest_sha256'})
            with self.assertRaises(ValueError):validate_manifest(self.root/'packets',altered,encode(altered))

    def test_default_live_guard_precedes_custody_and_credential_access(self):
        build(self.root/'packets')
        with self.assertRaisesRegex(ValueError,'LIVE_LAUNCH_NOT_APPROVED'):
            engine.create(self.root/'must-not-exist',self.root/'packets')
        self.assertFalse((self.root/'must-not-exist').exists())

    def test_research_rules_do_not_approve_RD03_or_policy(self):
        r=rules();self.assertEqual(r['approval'],'NOT APPROVED')
        self.assertIn('RD03_not_approved',r['proposed']['justification'])
        self.assertIn('0.5',r['proposed']['carl_thresholds']['claim_supported'])
        self.assertEqual(len(r['proposed']['sources']),3)
        self.assertFalse(assurance()['release_authority'])

    def test_current_binary_closure_and_model_bound(self):
        from .contract import routes
        for key in ('gemini','haiku','sol'):
            binding=routes()[key];profile.verify_binding(binding)
            self.assertIn(binding['model'],binding['argv'])
            if key!='sol':
                self.assertNotIn('--no-remote-export',binding['argv'])
                self.assertEqual(binding['argv'][binding['argv'].index('--sync-session')+1],'off')

    def _execute(self,generator,scenario):
        m=build(self.root/'packets',fixture_route=self.route)
        p=next(p for p in m['positions'] if p['generator']==generator and p['arm']=='B0')
        m['transport']['scenarios']={p['id']:scenario};m['manifest_sha256']=digest({k:v for k,v in m.items() if k!='manifest_sha256'})
        (self.root/'packets/manifest.json').write_bytes(encode(m))
        campaign=engine.create(self.root/'campaign',self.root/'packets');db=engine.connect(campaign)
        self.assertTrue(engine.reserve(db,campaign,m,p))
        with engine.transaction(db):
            db.execute("UPDATE positions SET state='started' WHERE id=?",(p['id'],));engine.event(db,'started',p['id'],{})
        req=decode(db.execute('SELECT request FROM attempts WHERE id=?',(p['id'],)).fetchone()[0])
        engine.execute_transport(db,campaign,m,p,req,None)
        with self.assertRaises(ValueError):engine.execute_transport(db,campaign,m,p,req,None)
        count=db.execute('SELECT count(*) FROM invocations').fetchone()[0]
        self.assertEqual(count,1)
        db.close();report=engine.verify(campaign)
        return report['receipts'][p['id']],report

    def test_actual_Copilot_fixture_profile_custody(self):
        receipt,report=self._execute('gemini','valid')
        self.assertEqual(receipt['state'],'completed')
        self.assertEqual(receipt['assurance']['designation'],DESIGNATION)
        self.assertEqual(receipt['CLI_evidence']['top_level_CLI_launches'],1)
        self.assertEqual(receipt['CLI_evidence']['raw_evidence'],'CLI_stdout_stderr_events_NOT_provider_HTTP')
        self.assertFalse(receipt['strict_scientific_pooling_permitted'])

    def test_Codex_missing_serving_identity_does_not_fabricate_it(self):
        receipt,_=self._execute('sol','valid')
        self.assertEqual(receipt['state'],'completed')
        self.assertIsNone(receipt['observed_identity'])
        self.assertEqual(receipt['CLI_evidence']['serving_identity_status'],'unavailable')

    def test_tool_attempt_unavailable_no_reinvocation(self):
        receipt,_=self._execute('haiku','cli_tools');self.assertEqual(receipt['state'],'unavailable')
        self.assertIn('watchdog',receipt['CLI_evidence']['failure'])

    def test_credential_echo_not_persisted_or_hashed(self):
        from .cli import DUMMY
        receipt,_=self._execute('gemini','cli_credential_echo')
        self.assertEqual(receipt['state'],'unavailable')
        self.assertTrue(receipt['CLI_evidence']['credential_capture_refused'])
        for p in (self.root/'campaign').rglob('*'):
            if p.is_file():
                self.assertNotIn(DUMMY.encode(),p.read_bytes())
                self.assertNotIn(base64.b64encode(DUMMY.encode()),p.read_bytes())


if __name__=='__main__':unittest.main()
