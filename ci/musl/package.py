"""Package the installed prefix, with its scope and external dependencies."""
import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path

work = Path('/work')
source = Path('/src')
dist = work / 'dist'
licenses = work / 'licenses'
licenses.mkdir()
for name in ['pinocchio', 'eigenpy', 'coal', 'console_bridge', 'urdfdom_headers', 'urdfdom', 'octomap']:
    for path in (work / name).iterdir():
        if path.is_file() and path.name.upper().startswith(('LICENSE', 'COPYING')):
            shutil.copy2(path, licenses / f'{name}-{path.name}')
shutil.copy2(work / 'build/boost_1_89_0/LICENSE_1_0.txt', licenses / 'boost-LICENSE_1_0.txt')
audit = json.loads((work / 'logs/elf-audit.json').read_text())
manifest = {
    'project': 'pinocchio', 'version': '3.9.0', 'python': platform.python_version(),
    'numpy': '2.3.5', 'platform': 'linux-musl-x86_64',
    'source_commit': subprocess.check_output(['git', '-C', '/src', 'rev-parse', 'HEAD'], text=True).strip(),
    'dependencies': json.loads((source / 'ci/musl/dependencies.json').read_text()),
    'artifact_kind': 'installed-prefix, not a wheel or self-contained Python runtime',
    'features': {'python': True, 'urdf': True, 'coal': True, 'octomap': True, 'qhull': True, 'openmp': False, 'extra_algorithms': False},
    'elf_files_checked': len(audit),
    'external_files': sorted(row['path'] for row in audit if not row['path'].startswith('/work/prefix/')),
    'tests': 'functional and selected upstream Python tests; full Robot SDK/installer not included',
}
(dist / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
archive = dist / 'pinocchio-3.9.0-cp313-musl-x86_64-prefix.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    tar.add(work / 'prefix', arcname='prefix')
    tar.add(licenses, arcname='licenses')
    tar.add(dist / 'build-manifest.json', arcname='build-manifest.json')
    tar.add(source / 'ci/musl/README.md', arcname='README.md')
shutil.copy2(source / 'ci/musl/README.md', dist / 'RELEASE_NOTES.md')
paths = [archive, dist / 'build-manifest.json']
(dist / 'SHA256SUMS').write_text(''.join(f'{hashlib.file_digest(p.open("rb"), "sha256").hexdigest()}  {p.name}\n' for p in paths))
