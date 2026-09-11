"""Fetch the exact dependency revisions used by the musl build."""
import json
import subprocess
from pathlib import Path

source = Path('/src')
work = Path('/work')
dependencies = json.loads((source / 'ci/musl/dependencies.json').read_text())
for name, spec in dependencies.items():
    target = work / name
    subprocess.run(['git', 'init', '-q', str(target)], check=True)
    subprocess.run(['git', '-C', str(target), 'remote', 'add', 'origin', spec['url']], check=True)
    subprocess.run(['git', '-C', str(target), 'fetch', '--depth', '1', 'origin', spec['commit']], check=True)
    subprocess.run(['git', '-C', str(target), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != spec['commit']:
        raise RuntimeError(f'{name}: unexpected source revision {actual}')
    if spec['cmake_submodule']:
        subprocess.run(['git', '-C', str(target), 'submodule', 'update', '--init', '--depth', '1', 'cmake'], check=True)
for name, patch in [
    ('urdfdom', 'urdfdom-gcc15-cstdint.patch'),
    ('urdfdom_headers', 'urdfdom-headers-gcc15-cstdint.patch'),
    ('coal', 'coal-boost189-system.patch'),
]:
    subprocess.run(['git', '-C', str(work / name), 'apply', str(source / 'ci/musl/patches' / patch)], check=True)
