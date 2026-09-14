"""Run using a separate standalone CPython, with the build prefix unavailable."""
import ctypes, hashlib, importlib.metadata, json, os, sys, tempfile
from pathlib import Path
import numpy as np
import eigenpy, coal, pinocchio as pin
import semantic_windows_native
assert sys.version_info[:2] == (3,13)
assert np.__version__ == '2.3.5'
assert pin.__version__ == '3.9.0'
assert importlib.metadata.version('eigenpy') == '3.12.0'
assert importlib.metadata.version('coal') == '3.0.2'
model=pin.buildSampleModelManipulator();data=model.createData();q=pin.neutral(model)
pin.forwardKinematics(model,data,q)
pin.computeAllTerms(model,data,q,np.zeros(model.nv))
assert np.isfinite(data.M).all()
assert np.isfinite(pin.rnea(model,data,q,np.zeros(model.nv),np.zeros(model.nv))).all()
with tempfile.TemporaryDirectory(prefix='Semantic Windows ') as folder:
    root=Path(folder)
    (root/'mesh.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n')
    (root/'robot.urdf').write_text('''<robot name="test"><link name="base"><collision><geometry><mesh filename="mesh.obj"/></geometry></collision></link><link name="tip"><collision><geometry><box size="0.1 0.1 0.1"/></geometry></collision></link><joint name="move" type="prismatic"><parent link="base"/><child link="tip"/><axis xyz="1 0 0"/><limit lower="0" upper="5" effort="1" velocity="1"/></joint></robot>''')
    robot, collision, visual=pin.buildModelsFromUrdf(str(root/'robot.urdf'), package_dirs=[str(root)])
    assert len(collision.geometryObjects)==2
    collision.addAllCollisionPairs()
    geometry=pin.GeometryData(collision)
    pin.computeCollisions(robot,robot.createData(),collision,geometry,np.array([3.0]),False)
    assert not any(result.isCollision() for result in geometry.collisionResults)
modules=(ctypes.c_void_p*2048)();needed=ctypes.c_ulong()
process=ctypes.windll.kernel32.GetCurrentProcess
process.restype=ctypes.c_void_p
assert ctypes.windll.psapi.EnumProcessModules(ctypes.c_void_p(process()),ctypes.byref(modules),ctypes.sizeof(modules),ctypes.byref(needed))
loaded=[]
for module in modules[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
    buffer=ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.kernel32.GetModuleFileNameW(ctypes.c_void_p(module),buffer,len(buffer))
    loaded.append(buffer.value)
private_dlls = Path(semantic_windows_native.__file__).parent / '.libs'
assert (private_dlls/'msvcp140.dll').is_file()
assert (private_dlls/'vcruntime140.dll').is_file()
for path in loaded:
    assert 'pinocchio-build-env' not in path.lower(),path
    assert 'miniconda' not in path.lower(),path
    # The hosted runner has VC redistributables installed. Do not let those
    # conceal an incomplete archive. The base interpreter may own its CRT.
    if Path(path).name.lower().startswith(('msvcp140', 'vcruntime140', 'concrt140')):
        assert any(Path(path).resolve().is_relative_to(root.resolve())
                   for root in [private_dlls, Path(sys.base_prefix)]), path
report={'python':sys.version,'numpy':np.__version__,'pinocchio':pin.__version__,'urdf_mesh_collision':True,'fk_rnea':True,'loaded_modules':loaded}
Path(sys.argv[1]).write_text(json.dumps(report,indent=2))
print('PASS standalone CPython, FK/RNEA, URDF, mesh loading, collision and DLL closure')
