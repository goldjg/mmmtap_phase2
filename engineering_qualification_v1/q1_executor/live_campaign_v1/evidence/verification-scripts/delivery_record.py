import json,sqlite3,subprocess,hashlib,sys
from pathlib import Path
from collections import Counter
from engineering_qualification_v1.q1_executor import engine
from engineering_qualification_v1.q1_executor.model import decode,encode,raw_hash,digest,validate_manifest
from engineering_qualification_v1.q1_executor.transport_qualification import snapshot
from engineering_qualification_v1.q1_executor.live_campaign_v1.launch import blockers,PRODUCTION_AUTHORITY
root=Path.cwd();package=root/'engineering_qualification_v1/q1_executor/live_campaign_v1';e=package/'evidence';campaign=e/'qualified-full-campaign/campaign'
code_commit=sys.argv[1]
assert len(code_commit)==40
before=snapshot(campaign);report=engine.verify(campaign);assert snapshot(campaign)==before
assert (e/'qualified-full-campaign/server.stderr').read_bytes()==b'', 'fixture_reported_unexpected_request_or_error'
accept=decode((e/'qualified-full-campaign/acceptance.json').read_bytes());assert accept['scheduled_positions']==153 and report['summary']['all_positions_terminal']
production,_=validate_manifest(package/'sealed-campaign');local=report['manifest']
assert production['positions']==local['positions'] and production['packets']==local['packets']
assert production['production_campaign']['routes']==local['production_campaign']['routes']
db=engine.connect(campaign,readonly=True)
usage=Counter();usage_reports=0;unknown_usage=[]
for ident,r in db.execute('SELECT id,record FROM transports'):
 if not r:continue
 rec=decode(r);meta=rec.get('https') or {};u=meta.get('usage')
 if u is not None:
  usage_reports+=1
  for key in ['input_tokens','output_tokens','cached_input_tokens','cache_write_tokens','total_tokens']:
   if type(u.get(key)) is int:usage[key]+=u[key]
 elif meta.get('client_POSTs'):unknown_usage.append(ident)
interrupt=db.execute('SELECT body FROM receipts WHERE id=?',('c02-sol-r1-e3-nc-g1',)).fetchone()[0]
interrupt=decode(interrupt)
assert interrupt['state']=='interrupted' and interrupt['https']['response_entity_bytes']>0
assert interrupt['https']['client_POSTs']==1
pairs=Counter(tuple(r['preceding_disposition_pair']) for r in report['receipts'].values() if r['preceding_disposition_pair'])
db.close()
record={
 'status':'Q1 LIVE LAUNCH BLOCKED — EXACT REMAINING DECISIONS IDENTIFIED',
 'implementation_commit':code_commit,'source_baseline':'54b8762ecdc48b96ebd3ae5f394b995c89cc9094',
 'launch_approval':'NOT APPROVED','manifest_file_sha256':raw_hash((package/'sealed-campaign/manifest.json').read_bytes()),
 'manifest_sha256':production['manifest_sha256'],'packets':production['packets'],
 'Choice1_PI_decision':{'path':'engineering_qualification_v1/q1_executor/systemone_typed_v1/PI_DECISION.md','sha256':raw_hash((root/'engineering_qualification_v1/q1_executor/systemone_typed_v1/PI_DECISION.md').read_bytes())},
 'schedule':{'positions':153,'generators':99,'native_SystemOne':27,'carl_SystemOne':27,'repetitions':1,'arms':8,'dependency_edges':198},
 'routes':production['production_campaign']['routes'],
 'authorised_real_dispatches_now':0,
 'maximum_proposed_local_scope':{'reservations':153,'CLI_invocations':99,'SystemOne_client_POSTs':54,'harness_retries':0,'fallbacks':0,'replacement_attempts':0,'provider_executions':None,'CLI_internal_HTTP_attempts':None,'release_authority':False},
 'bounds':{'request_entity_bytes':262144,'response_entity_bytes':262144,'response_header_bytes':16384,'provider_deadline_seconds':5,'supervisor_seconds':25,'token_ceiling':None,'financial_ceiling':None,'expected_live_tokens':None,'expected_live_cost':None,'reason':'No verified current tariff/account cap; local bytes/time and invocation counts do not bound provider work, CLI retries or billing.'},
 'offline_qualification':{'record':'qualified-full-campaign/acceptance.json','sha256':raw_hash((e/'qualified-full-campaign/acceptance.json').read_bytes()),'observed':{k:accept[k] for k in ['scheduled_positions','outcomes','actual_local_POSTs','POSTs_by_route','reservation_ceiling_exercised','restart_no_retransmission','credential_absent_from_custody','carl_policy_positive_and_no_challenge_cases','inadmissible_specialist_inputs_consumed_without_credential_or_POST','negative_checks']},'transport_mode':'actual worker/broker/local TLS; subscription CLI event injection, not actual CLI execution','real_provider_calls':0,'actual_generator_CLI_invocations':0,'evidence_tip_sha256':report['summary']['evidence_tip_sha256'],'read_only_reconstruction_unchanged':True},
 'accounting':{'context':'local fixtures only, never real provider usage or financial accounting','all_returned_usage_reports_including_invalid_unavailable_and_HTTP_errors':usage_reports,'reported_tokens':dict(usage),'POSTs_with_unknown_usage':unknown_usage,'reservation_budget_exercised':141,'production_local_reservation_ceiling':153,'never_refunded':True},
 'dispositions':{'context':'injected outputs only; not scientific results','preceding_movement_pairs':[{'from':a,'to':b,'count':n} for (a,b),n in sorted(pairs.items())],'intermediate_and_final_receipts':True,'invalid_unavailable_not_unchanged':True,'unsuccessful_parent_descendants_censored':True},
 'policy_versions':{'governing':'rd05-synthetic-policy-v1_candidate_NOT_APPROVED','challenge':'q1-proposed-historical-carl-policy-v1_NOT_APPROVED','applied_thresholds':'default historical pack 0.5; cautious override not activated','continuation':'PROPOSED_fixed_scheduled_turns_even_when_no_challenge; no extra turns','failure':'PROPOSED_censor_descendants_continue_independent_branches'},
 'custody':{'offline_directory':str(campaign),'prospective_production_authority':str(PRODUCTION_AUTHORITY),'authority_provisioned':False,'single_canonical_custody_and_database_inode_with_deployment_flock':True,'cross_host_exactly_once_or_operator_rollback_protection':False,'recovery':'Verify read-only, resume same authoritative directory; outstanding reservations become interrupted; no retransmission, rebinding, fallback or repair.','interrupted_prefix_bytes':interrupt['https']['response_entity_bytes']},
 'provider_assurances':{'historical_SystemOne_access':'VERIFIED_HISTORIC; not newly onboarded','current_fixed_revision_and_account_entitlement':'UNKNOWN_operator_confirmation_required_without_authentication_in_this_task','returned_SystemOne_model':'unsigned response self-report, not independent serving attestation','Codex_observed_served_model':None,'remote_retries_replay_execution_count':'UNKNOWN','timeout_execution_and_billing_reconciliation':'UNKNOWN','request_correlation':'capture safe provider IDs if supplied; local sealed association is not provider request attestation','usage':'raw returned metadata retained separately from financial accounting'},
 'remaining_actions_priority_order':[
  {'owner':'PI','action':'Retain strict generator requirements (NO-GO), or explicitly approve a different lower-assurance subscription CLI design, including internal attempts/network/tools and missing Codex serving identity.','code_effect':'Strict production CLI broker binding is not implemented; a changed assurance contract would require a separately qualified binding, not a manifest switch.'},
  {'owner':'operator','action':'Restore pinned Copilot/Codex runtime closures or select and qualify current closures offline; current Copilot pins differ and pinned Codex is absent.'},
  {'owner':'PI','action':'Approve exact source role/sufficiency, governing policy, challenge thresholds and continuation/failure rules. RD05 fictional obligations are not discharged by the authored short source strings.'},
  {'owner':'operator','action':'Provision reviewed production IPv4:443, explicit CA, routed broker namespace, exact nft rules/inspection privilege and fixed persistent authority directory. No host configuration changed here.'},
  {'owner':'operator/provider and PI','action':'Confirm current entitlement/fixed revision/account pricing and spend limits; accept or resolve unsigned identity, remote replay and timeout/billing uncertainties.'},
  {'owner':'PI','action':'Only after blockers are resolved, explicitly authorize the exact code/manifest/packet hashes and maximum local scope. This record grants no launch authority.'}],
 'full_live_launch_immediately_after_generic_PI_approval':False,
 'production_launch_entrypoint':'intentionally unlaunchable under current strict unqualified CLI contract; no automatic enablement path',
 'frozen_worker_instruments_historical_custody_preserved':True,
 'verification':{'focused_tests':48,'historical_campaigns_readonly':87,'historical_seal_sets':10,'historical_sealed_entries':2548,'original_custody_entries':40538},
}
(e/'launch-record.json').write_bytes(encode(record))
verification={'production_manifest_disabled':True,'same_positions_packets_and_provider_routes_as_exercised_configuration':True,'differences':['local TEST-NET TLS route instead of absent production route','explicit fault injection','141 local reservation units to exercise exhaustion, production ceiling 153'],'qualified_campaign_summary':report['summary'],'source_commit':code_commit,'unapproved_scientific_decisions':True,'real_provider_calls':0}
(e/'verification.json').write_bytes(encode(verification))
print(encode({'commit':code_commit,'offline_outcomes':accept['outcomes'],'POSTs':accept['actual_local_POSTs'],'usage_reports':usage_reports,'manifest':production['manifest_sha256']}).decode())
