"""Package Windows Pinocchio and locked EigenPy/Coal with a private DLL closure."""
import hashlib, json, shutil, sys
from pathlib import Path
from wheel.wheelfile import WheelFile

prefix, installed, output = map(Path, sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
work = output / 'wheel-staging'
work.mkdir()
lock = json.loads((Path(__file__).with_name('conda-lock.json')).read_text())


def wheel(name, version, files, requirements=()):
    root = work / name
    for src, relative in files:
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    metadata = root / f'{name}-{version}.dist-info'
    metadata.mkdir(parents=True)
    (metadata/'METADATA').write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n' + ''.join('Requires-Dist: '+r+'\n' for r in requirements) + '\n')
    (metadata/'WHEEL').write_text('Wheel-Version: 1.0\nGenerator: insightos-windows\nRoot-Is-Purelib: false\nTag: cp313-cp313-win_amd64\n')
    path = output / f'{name}-{version}-cp313-cp313-win_amd64.whl'
    with WheelFile(path, 'w') as archive:
        archive.write_files(root)
    return path

native = work / 'native-input'
(native/'.libs').mkdir(parents=True)
# Each source package has a pinned hash in conda-lock.json. Never copy Python's
# runtime DLL into the extension closure; the installed base interpreter owns it.
for folder in [prefix/'Library/bin', installed/'bin', installed/'lib']:
    if not folder.exists(): continue
    for dll in folder.glob('*.dll'):
        if dll.name.lower().startswith('python3'): continue
        dest = native/'.libs'/dll.name
        if dest.exists() and dest.read_bytes() != dll.read_bytes():
            raise RuntimeError(f'conflicting DLL: {dll.name}')
        shutil.copyfile(dll, dest)
(native/'__init__.py').write_text('''import os
from pathlib import Path
_handles = [os.add_dll_directory(str(Path(__file__).parent / ".libs"))]
def activate():
    return _handles
''')
licenses = native/'licenses'
licenses.mkdir()
for source in (prefix/'conda-meta').glob('*.json'):
    record = json.loads(source.read_text())
    target = licenses / record['name']
    target.mkdir()
    (target/'metadata.json').write_text(json.dumps({k:record.get(k) for k in ['name','version','build','license','url','sha256']},indent=2))
    extracted = Path(record.get('extracted_package_dir', ''))
    if extracted.is_dir() and (extracted/'info/licenses').is_dir():
        shutil.copytree(extracted/'info/licenses', target/'texts')
shutil.copyfile(Path(__file__).parents[2]/'LICENSE', licenses/'pinocchio-LICENSE')
shutil.copyfile(Path(__file__).with_name('conda-lock.json'), native/'conda-lock.json')
wheel('semantic_windows_native', '3.9.0', [(p, Path('semantic_windows_native')/p.relative_to(native)) for p in native.rglob('*') if p.is_file()])

for distribution, version, modules, site in [
    ('eigenpy','3.12.0',['eigenpy'],prefix/'Lib/site-packages'),
    ('coal','3.0.2',['coal','hppfcl'],prefix/'Lib/site-packages'),
    ('pin','3.9.0',['pinocchio'],installed/'Lib/site-packages'),
]:
    files = []
    for module in modules:
        source = site / module
        if not source.is_dir(): raise RuntimeError(f'missing module {source}')
        for path in source.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc': continue
            relative = path.relative_to(site)
            if relative == Path(module)/'__init__.py':
                patched = work / f'{module}-init.py'
                content = path.read_text(encoding='utf-8')
                # Insert before imports without breaking any __future__ directives.
                import ast
                tree = ast.parse(content)
                line = 0
                for node in tree.body:
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value,str): line=node.end_lineno; continue
                    if isinstance(node, ast.ImportFrom) and node.module=='__future__': line=node.end_lineno; continue
                    break
                lines=content.splitlines(keepends=True)
                lines.insert(line, 'import semantic_windows_native as _semantic_native\n_semantic_native.activate()\n')
                patched.write_text(''.join(lines), encoding='utf-8')
                path=patched
            files.append((path,relative))
    requires=['numpy==2.3.5','semantic-windows-native==3.9.0']
    if distribution in ['coal','pin']: requires += ['eigenpy==3.12.0']
    if distribution=='pin': requires += ['coal==3.0.2']
    wheel(distribution,version,files,requires)
shutil.rmtree(work)
print(json.dumps({'wheels':[p.name for p in output.glob('*.whl')]},indent=2))
