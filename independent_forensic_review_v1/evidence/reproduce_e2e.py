import json,hashlib
from pathlib import Path
from phase2.core import load,corpus
from phase2.integration import ScriptedAdapters,PILOT_CASES
from phase2.engine import execute
from phase2.adjudication import checked_records,blind_export
root=Path('/home/prometheus/git/mmmtap_phase2')
out=root/'independent_forensic_review_v1/evidence'
plan=load(root/'integration_readiness_v1/execution_plan_v3.json');_,members=corpus()
run=out/'reproduced_e2e';mock=ScriptedAdapters(plan)
selection={(c,'baseline') for c in PILOT_CASES}
first=execute(plan,members,run,mode='mock',selected_inputs=selection,mock=mock)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):h(p) for p in (run/'checkpoints').rglob('*') if p.is_file()}
second=execute(plan,members,run,mode='mock',selected_inputs=selection,mock=mock)
assert before=={str(p):h(p) for p in (run/'checkpoints').rglob('*') if p.is_file()}
p,records=checked_records(run)
export=blind_export(run,members,out/'reproduced_blinded',out/'reproduced_private_key.json')
print(json.dumps({'first':first,'resume':second,'checkpoint_bytes_unchanged':True,'records_verified':len(records),'export':export,'actual_model_calls':0,'native_systemone_calls':0},indent=2))
