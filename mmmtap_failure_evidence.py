#!/usr/bin/env python3
"""Read-only MMMTAP pilot failure evidence collector (standard library only).

Creates a compact ZIP with sanitized failure diagnostics. It never modifies
run checkpoints, ledger, manifests, or operator code.
"""
import argparse
import base64
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXPECTED = {'case_id', 'variant_id', 'claims', 'disposition', 'uncertainties', 'changes'}
SUCCESS = {'ok', 'mock_ok'}
REDACT_KEY = re.compile(r'(token|secret|password|authorization|credential|api.?key|private.?key|cookie)', re.I)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_value(value, limit=400):
    if isinstance(value, str):
        return value[:limit] + ('… [truncated]' if len(value) > limit else '')
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f'<{type(value).__name__}>'


def shape_diff(obj, previous):
    if not isinstance(obj, dict):
        return {'response_type': type(obj).__name__}
    diag = {
        'response_top_level_keys': sorted(obj),
        'extra_top_level_keys': sorted(set(obj) - EXPECTED),
        'missing_top_level_keys': sorted(EXPECTED - set(obj)),
        'case_id': safe_value(obj.get('case_id')),
        'variant_id': safe_value(obj.get('variant_id')),
        'disposition': safe_value(obj.get('disposition')),
    }
    claims = obj.get('claims')
    changes = obj.get('changes')
    if not isinstance(claims, list) or not isinstance(changes, list):
        diag['claims_type'] = type(claims).__name__
        diag['changes_type'] = type(changes).__name__
        return diag
    prior = {c['claim_id']: c for c in (previous or {}).get('claims', []) if isinstance(c, dict) and isinstance(c.get('claim_id'), str)}
    current = {c['claim_id']: c for c in claims if isinstance(c, dict) and isinstance(c.get('claim_id'), str)}
    declared = {c['claim_id']: c for c in changes if isinstance(c, dict) and isinstance(c.get('claim_id'), str)}
    diag['prior_claim_ids'] = sorted(prior)
    diag['current_claim_ids'] = sorted(current)
    diag['accounted_claim_ids'] = sorted(declared)
    diag['missing_change_accounting'] = sorted((set(prior) | set(current)) - set(declared))
    diag['unexpected_change_accounting'] = sorted(set(declared) - (set(prior) | set(current)))
    diag['change_actions'] = {k: safe_value(v.get('action')) for k, v in declared.items()}
    diff = []
    for ident in sorted(set(prior) & set(current)):
        old, new = prior[ident], current[ident]
        fields = [key for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)]
        if fields:
            diff.append({'claim_id': ident, 'declared_action': safe_value(declared.get(ident, {}).get('action')),
                         'changed_fields': fields,
                         'field_summaries': {k: {'before': safe_value(old.get(k)), 'after': safe_value(new.get(k))}
                                             for k in fields}})
    diag['claim_differences'] = diff
    diag['unexpected_top_level_values'] = {
        k: '[REDACTED KEY]' if REDACT_KEY.search(k) else safe_value(obj[k])
        for k in sorted(set(obj) - EXPECTED)
    }
    return diag


def collect(root, include_all):
    entries = []
    for folder in sorted((root / 'checkpoints').iterdir()):
        if not folder.is_dir() or not (folder / 'result.json').is_file():
            continue
        result = load(folder / 'result.json')
        status = result.get('status')
        if status in SUCCESS or status in ('blocked_parent', 'not_attempted'):
            continue
        intent = load(folder / 'intent.json')
        job = intent['job']
        parent_id = job.get('assessment_parent')
        parent_file = root / 'checkpoints' / str(parent_id) / 'result.json' if parent_id else None
        previous = None
        if parent_file and parent_file.is_file():
            previous = load(parent_file).get('parsed')
        entry = {
            'job_id': folder.name, 'status': status, 'reason': result.get('reason'),
            'job': {k: job.get(k) for k in ('kind', 'generator', 'arm', 'turn', 'case_id', 'variant_id',
                                           'repetition', 'experimental_attempt', 'assessment_parent',
                                           'challenge_parent', 'template_key')},
            'evidence': {
                'manifest_sha256': result.get('manifest_sha256'),
                'instruments_sha256': result.get('instruments_sha256'),
                'result_file_sha256': sha(folder / 'result.json'),
                'raw_file_sha256': sha(folder / 'raw.json') if (folder / 'raw.json').is_file() else None,
                'parent_result_file_sha256': sha(parent_file) if parent_file and parent_file.is_file() else None,
                'model_requested': result.get('model_identity', {}).get('requested_model'),
                'model_observed': result.get('model_identity', {}).get('observed_model'),
                'exit_status': result.get('metrics', {}).get('exit_status'),
            },
        }
        raw_file = folder / 'raw.json'
        if raw_file.is_file():
            raw = load(raw_file)
            message = raw.get('message')
            if isinstance(message, str):
                try:
                    data = base64.b64decode(message, validate=True)
                    entry['response_sha256'] = hashlib.sha256(data).hexdigest()
                    obj = json.loads(data)
                    entry['diagnosis'] = shape_diff(obj, previous)
                except (ValueError, UnicodeDecodeError, TypeError) as exc:
                    entry['diagnosis'] = {'decode_or_json_error_type': type(exc).__name__}
            else:
                entry['diagnosis'] = {'message_type': type(message).__name__}
        entries.append(entry)
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('operator_runs_v1/pilot'))
    parser.add_argument('--output', type=Path, default=Path.home() / 'mmmtap-pilot-failures.zip')
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / 'checkpoints').is_dir():
        parser.error(f'Checkpoint directory not found: {root / "checkpoints"}')
    entries = collect(root, True)
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'source_run': str(root), 'failure_count': len(entries),
               'note': 'Derived, reduced diagnostics; consult immutable checkpoints for primary evidence.',
               'failures': entries}
    contents = json.dumps(summary, indent=2, ensure_ascii=False).encode('utf-8')
    # ZIP is saved outside the sealed run folder by default.
    output = args.output.expanduser().resolve()
    if output == root or root in output.parents:
        parser.error('Output cannot be inside the sealed run directory')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('pilot-failure-diagnostics.json', contents)
    print(f'Wrote {output} ({len(entries)} failures, {output.stat().st_size} bytes)')
    for e in entries:
        j=e['job']
        print(f"{j['generator']}/{j['arm']}/turn{j['turn']} {j['case_id']}/{j['variant_id']}: {e['reason']}")
    print('Review the ZIP before sharing. It contains reduced claim text and metadata, not raw telemetry.')

if __name__ == '__main__':
    main()
