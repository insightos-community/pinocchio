"""Audit the installed prefix and its resolved runtime dependency closure."""
import json
import os
import re
import subprocess
from pathlib import Path

prefix = Path('/work/prefix')
site_packages = Path('/usr/local/lib/python3.13/site-packages')
wheel_library_dirs = [str(p) for p in site_packages.glob('*.libs') if p.is_dir()]
pending = []
for root in [prefix, site_packages]:
    # Include dlopen'ed modules (not visible in the Python executable's NEEDED
    # entries), especially NumPy and its bundled OpenBLAS library.
    for path in root.rglob('*'):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream:
                if stream.read(4) == b'\x7fELF':
                    pending.append(path)
pending.append(Path('/usr/local/bin/python3'))
seen = set()
rows = []
while pending:
    path = pending.pop().resolve()
    if path in seen:
        continue
    seen.add(path)
    dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
    versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True)
    headers = subprocess.check_output(['readelf', '-l', str(path)], text=True)
    needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)
    # Python extension symbols are supplied by the interpreter at import time.
    # Preload libpython so standalone ldd checks model that host correctly.
    ldd = subprocess.run(
        ['ldd', str(path)], text=True, capture_output=True,
        env={
            **os.environ,
            'LD_PRELOAD': '/usr/local/lib/libpython3.13.so.1.0',
            # ldd on an individual wheel-private library has no parent module
            # RPATH context. Supply its wheel library directories explicitly;
            # the real import/functional tests do not need this addition.
            'LD_LIBRARY_PATH': ':'.join([str(prefix / 'lib'), *wheel_library_dirs]),
        },
    )
    dependencies = re.findall(r'=> (/\S+)', ldd.stdout)
    pending.extend(Path(dependency) for dependency in dependencies)
    rows.append({
        'path': str(path),
        'needed': needed,
        'glibc_versions': sorted(set(re.findall(r'\bGLIBC_[0-9.]+', versions))),
        'interpreter': re.findall(r'Requesting program interpreter: ([^\]]+)', headers),
        'ldd_returncode': ldd.returncode,
        'ldd_stdout': ldd.stdout,
        'ldd_stderr': ldd.stderr,
    })
output = Path('/work/logs/elf-audit.json')
output.write_text(json.dumps(rows, indent=2) + '\n')
assert not [r for r in rows if r['glibc_versions']], 'GLIBC symbols found'
assert not [r for r in rows if r['ldd_returncode']], 'Unresolved dependency or relocation'
print(f'PASS: {len(rows)} ELF files in prefix/Python/extensions dependency closure; no GLIBC version requirements')
print('Python interpreter:', next(r['interpreter'] for r in rows if r['path'].startswith('/usr/local/bin/python')))
