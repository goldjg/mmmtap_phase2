"""Prepare/qualify Q1 offline; live launch requires a separate exact PI record."""
import argparse
import os
from pathlib import Path

if 'JEVKEY' in os.environ or 'COPILOT_GITHUB_TOKEN' in os.environ:
    from ..systemone_https_v1.credential import harden
    harden()
from ..model import encode, validate_manifest
from .contract import build

parser=argparse.ArgumentParser(description=__doc__)
sub=parser.add_subparsers(dest='command',required=True)
for name in ('prepare','qualify'):
    p=sub.add_parser(name);p.add_argument('--output',required=True,type=Path)
p=sub.add_parser('launch',help='Requires a separately supplied PI launch decision; no approval is supplied by preparation.')
p.add_argument('--candidate',type=Path,required=True)
p.add_argument('--authorize-exact-manifest',required=True)
p.add_argument('--pi-record',type=Path,required=True)
p.add_argument('--pi-record-sha256',required=True)
args=parser.parse_args()
if args.command=='prepare':result=build(args.output.absolute())
elif args.command=='qualify':
    from .qualification import run
    result=run(args.output.absolute())
else:
    from .admission import authorise
    from .. import engine
    m,_=validate_manifest(args.candidate.absolute())
    if m['simulation_only']:raise ValueError('live_command_cannot_authorise_a_fixture')
    authorise(m,args.pi_record,args.pi_record_sha256,args.authorize_exact_manifest)
    custody=Path(m['launch_candidate']['custody_destination'])
    if not custody.exists():engine.create(custody,args.candidate.absolute())
    result=engine.resume(custody,offline_subprocess=True)
print(encode(result).decode())
