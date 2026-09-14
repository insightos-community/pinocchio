"""Publish verified Windows wheels without replacing a published release."""
import hashlib,json,os,re,subprocess
from pathlib import Path

root=Path('output')
tag=os.environ['TAG']
repo=os.environ['GITHUB_REPOSITORY']
if not re.fullmatch(r'windows-v3\.9\.0-[A-Za-z0-9][A-Za-z0-9.-]*',tag):
    raise ValueError('Invalid Windows component tag')
for line in (root/'SHA256SUMS').read_text().splitlines():
    checksum,name=line.split('  ',1)
    if name!=Path(name).name or hashlib.sha256((root/name).read_bytes()).hexdigest()!=checksum:
        raise ValueError('Artifact checksum mismatch')
report=json.loads((root/'windows-validation.json').read_text())
assert report['verification_commit']==os.environ['GITHUB_SHA']
assert report['fk_rnea'] and report['urdf_mesh_collision']
metadata=dict(schema_version=1,component='pinocchio',version='3.9.0',tag=tag,platform='windows-amd64',
              source_commit=report['source_commit'],verification_commit=report['verification_commit'],
              verification_run=f"https://github.com/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
              validation_scope='Standalone CPython 3.13.15 / NumPy 2.3.5; FK/RNEA, URDF, mesh, collision and bundled DLL checks. EigenPy/Coal/native dependencies are locked binary inputs. Installer and physical GPU validation are separate.')
(root/'release.json').write_text(json.dumps(metadata,indent=2)+'\n')
(root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(root.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
existing=subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','isDraft'],capture_output=True)
if existing.returncode==0:
    if not json.loads(existing.stdout)['isDraft']:
        subprocess.run(['gh','release','download',tag,'--repo',repo,'--pattern','release.json','--dir','existing-release'],check=True)
        old=json.loads(Path('existing-release/release.json').read_text())
        assert old['source_commit']==metadata['source_commit'] and old['verification_commit']==metadata['verification_commit']
        print('Matching published release already exists; assets preserved')
        raise SystemExit(0)
else:
    subprocess.run(['gh','release','create',tag,'--repo',repo,'--target',os.environ['GITHUB_SHA'],'--draft','--prerelease',
                    '--title','Pinocchio 3.9.0 / Windows CPython 3.13','--notes',metadata['validation_scope']],check=True)
subprocess.run(['gh','release','upload',tag,'--repo',repo,'--clobber',*map(str,sorted(root.iterdir()))],check=True)
subprocess.run(['gh','release','edit',tag,'--repo',repo,'--draft=false'],check=True)
