"""Explicit exact-candidate launch authorisation, never a manifest enable flag.

No authorised record exists in this increment. The future trusted operator must
supply a PI decision record AND explicitly name this manifest digest on the CLI.
The immutable candidate retains NOT APPROVED; the separate launch decision is
durable custody evidence. Merely editing the candidate cannot activate it.
"""
import os
from pathlib import Path
import sqlite3

from ..model import decode, encode, digest, raw_hash
from . import VERSION

ACTIVE = None


def validate_decision(m, raw):
    from .contract import assurance, base
    record = decode(raw)
    fields={"version","manifest_sha256","implementation_sha256","assurance_sha256","approved_proposals_sha256",
        "maximum_local_invocations","maximum_generator_invocations","maximum_SystemOne_POSTs",
        "accepted_limitations_sha256","PI_identity","PI_decision_reference","launch_decision","account_and_cost_acceptance",
        "deployment_route","broker_namespaces"}
    if (set(record)!=fields or record['version']!=VERSION+'-explicit-PI-launch-v1'
            or record['manifest_sha256']!=m['manifest_sha256'] or record['implementation_sha256']!=digest(m['transport']['specification'])
            or record['assurance_sha256']!=digest(assurance())
            or record['approved_proposals_sha256']!=m['packets']['research_rule_proposals']['sha256']
            or record['accepted_limitations_sha256']!=digest(assurance()['unqualified'])
            or (record['maximum_local_invocations'],record['maximum_generator_invocations'],record['maximum_SystemOne_POSTs'])!=(153,99,54)
            or record['launch_decision']!='APPROVED'
            or any(not isinstance(record[k],str) or not record[k].strip() for k in
                ('PI_identity','PI_decision_reference','account_and_cost_acceptance'))):
        raise ValueError('exact_PI_launch_decision_required_NOT_APPROVED_by_this_task')
    base.validate_route(record['deployment_route'],fixture=False)
    if record['deployment_route'] is None:raise ValueError('reviewed_production_deployment_required')
    ns=record['broker_namespaces']
    if set(ns)!={'network_path','network_inode','user_path','user_inode'} or ns['network_inode']!=record['deployment_route']['network_namespace']:
        raise ValueError('broker_namespace_binding_required')
    for key in ('network_path','user_path'):
        if not isinstance(ns[key],str) or not ns[key].startswith('/'):raise ValueError('namespace_handle_must_be_absolute')
    return record


def authorise(m, record_path, record_sha256, explicitly_authorised_manifest):
    global ACTIVE
    if explicitly_authorised_manifest!=m['manifest_sha256']:
        raise ValueError('explicit_command_for_exact_manifest_required')
    raw=Path(record_path).read_bytes()
    if raw_hash(raw)!=record_sha256:raise ValueError('PI_record_digest_changed')
    record=validate_decision(m,raw)
    ACTIVE=(m['manifest_sha256'],raw,record)


def require_authorisation(m):
    global ACTIVE
    if ACTIVE is None or ACTIVE[0]!=m['manifest_sha256']:
        root=Path(m['launch_candidate']['custody_destination'])
        try:
            from .. import engine
            db=engine.connect(root,readonly=True)
            try:creation=decode(db.execute("SELECT value FROM meta WHERE key='creation'").fetchone()[0])
            finally:db.close()
            raw=(root/'launch-authorisation.json').read_bytes()
            if raw_hash(raw)!=creation['launch_authorisation_sha256']:raise ValueError('custody_launch_record_changed')
            record=validate_decision(m,raw)
            ACTIVE=(m['manifest_sha256'],raw,record)
        except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
            raise ValueError('Q1_LOWER_ASSURANCE_LIVE_LAUNCH_NOT_APPROVED_exact_PI_decisions_and_explicit_command_required') from None
    return ACTIVE


def route(m):
    return m['production_campaign']['fixture_route'] if m['simulation_only'] else require_authorisation(m)[2]['deployment_route']


def broker_prefix(m):
    if m['simulation_only']:return []
    record=require_authorisation(m)[2];ns=record['broker_namespaces']
    for kind in ('user','network'):
        handle=ns[kind+'_path']
        if os.readlink(handle)!=ns[kind+'_inode']:
            # proc namespace handles are symlinks; mounted namespace handles
            # may instead be reviewed proc paths. No broad host setns fallback.
            raise ValueError('reviewed_broker_namespace_handle_changed')
    pin=m['transport']['specification']['bindings']['nsenter']
    if raw_hash(Path(pin['path']).read_bytes())!=pin['sha256']:raise ValueError('nsenter_binary_changed')
    prefix=[pin['path']]
    if os.readlink('/proc/self/ns/user')!=ns['user_inode']:
        prefix+=['--user='+ns['user_path'],'--preserve-credentials']
    return prefix+['--net='+ns['network_path'],'--']
