"""Read-only target reproduction; new inputs live only in temporary directories."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, '/home/prometheus/git/mmmtap_phase2')
from phase2 import core, integration

root = Path('/home/prometheus/git/mmmtap_phase2')
instruments = root / 'integration_readiness_v1/instruments'
source, _ = core.corpus()
original = core.load(root / 'integration_readiness_v1/execution_plan_v3.json')
results = {}
with tempfile.TemporaryDirectory(prefix='forensic-instrument-') as tmp:
    # Redirect only the planner's package reads into a scratch copy. The source
    # corpus and original frozen instrument directory remain read-only.
    package = Path(tmp)/'phase2'
    package.mkdir()
    for p in (root/'phase2').glob('*.py'):
        shutil.copyfile(p, package/p.name)
    templates = core.load(root/'phase2/prompts.v1.json')
    templates['C1'] += '\nFORENSIC_NEW_SELF_REVIEW_INSTRUCTION_NOT_IN_FROZEN_SNAPSHOT'
    (package/'prompts.v1.json').write_bytes(core.json_bytes(templates))
    with patch.object(core, 'PACKAGE', package):
        altered_plan = integration.plan_v3(instruments, source, original['readiness_snapshot'])
        integration.validate_v3(altered_plan)
    results['prompt_freeze_bypass'] = {
        'validate_v3_accepted': True,
        'original_instrument_digest_reused': altered_plan['instruments_sha256'] == original['instruments_sha256'],
        'new_plan_digest': altered_plan['manifest_sha256'],
        'original_plan_digest': original['manifest_sha256'],
        'planned_prompt_differs_from_frozen_snapshot': altered_plan['prompt_templates'] != core.load(instruments/'prompts.v1.snapshot.json'),
        'qualification_or_provider_calls': 0,
        'original_target_files_modified': False,
        'caveat': 'Fresh plan construction under a scratch PACKAGE override, not acceptance of a modified existing plan.'
    }

# The plan pins codex/bin/codex but mounts its whole release, containing other
# executable resources. This is an inventory observation, not helper tampering.
cfg = core.load(instruments/'config.v2.json')
release = Path(cfg['generators']['sol']['binary']).parent.parent
results['codex_unpinned_helpers'] = {}
for p in sorted(release.rglob('*')):
    if p.is_file() and p != Path(cfg['generators']['sol']['binary']):
        results['codex_unpinned_helpers'][str(p.relative_to(release))] = {
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'size': p.stat().st_size,
            'path_listed_in_frozen_config': str(p) in json.dumps(cfg),
            'hash_listed_in_frozen_config': hashlib.sha256(p.read_bytes()).hexdigest() in json.dumps(cfg)
        }
print(json.dumps(results, indent=2))
