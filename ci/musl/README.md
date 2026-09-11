# InsightOS musl build of Pinocchio 3.9.0

This fork's `insightos/musl` branch maintains the upstream **v3.9.0** source with a musl build pipeline. Upstream branches remain available. The Pinocchio algorithms are unchanged.

## Artifacts and runtime requirements

The `Musl build and release` workflow produces:

- `pinocchio-3.9.0-cp313-musl-x86_64-prefix.tar.gz`
- `build-manifest.json` and `SHA256SUMS`
- Separate build/test/ELF diagnostic artifacts in GitHub Actions.

The archive includes Pinocchio, Boost 1.89.0, EigenPy 3.12.0, Coal 3.0.2, URDF libraries and OctoMap, with Python bindings and project licenses. It is an **installed prefix**, not a pip wheel or a complete Python runtime. It requires musl x86_64, CPython 3.13, NumPy 2.3.5, and the system libraries listed in the manifest (including musl, libstdc++, libgcc, Assimp, Qhull, TinyXML2 and zlib). CMake installation paths were built for `/work/prefix`; CMake SDK relocation is not validated.

To use the Python bindings after extracting the archive:

```sh
export LD_LIBRARY_PATH="$PWD/prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="$PWD/prefix/lib/python3.13/site-packages${PYTHONPATH:+:$PYTHONPATH}"
python3 -c 'import pinocchio; print(pinocchio.__version__)'
```

Use a musl Python interpreter. These extensions cannot be loaded into a glibc Python process. This release does not claim complete installer or Alpine support for other components such as MuJoCo.

## Build and release

The workflow runs on a standard GitHub `ubuntu-24.04` runner, inside `python:3.13-alpine3.23` pinned by digest. It also supports local Docker builds from the repository root:

```sh
musl_work=$(mktemp -d)
docker run --rm --cpus=2 --memory=12g --memory-swap=12g \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=$musl_work,dst=/work" \
  python:3.13-alpine3.23@sha256:75f27d686432419c9d42420b2b9ef605868c7a0682a6be10a6601fad46c2df01 \
  sh /src/ci/musl/build.sh
```

Use an empty work directory outside the source checkout for every build.

Pushes and PRs to `insightos/musl`, and manual dispatches, build/test and upload artifacts. A tag matching `musl-v3.9.0-*` publishes a Release only after the build and tests succeed. Tags must point at the maintained branch containing this workflow. Example:

```sh
git tag -a musl-v3.9.0-1 -m 'Pinocchio 3.9.0 musl build 1'
git push origin musl-v3.9.0-1
```

Upstream version tags are not overwritten. A published Release is not replaced by a workflow rerun; use a new build tag. Failed uploads remain draft releases and can be retried.

## Adaptations and validation scope

- `dependencies.json` pins each dependency commit. Its upstream submodule pins select jrl-cmakemodules. Boost's source archive has a fixed SHA256.
- The two URDF patches add missing `<cstdint>` includes for GCC 15.
- The Coal patch avoids requesting the obsolete Boost.System binary component with Boost 1.89+.
- Coal's HPP-FCL compatibility, OctoMap and Qhull support are enabled. Python and URDF/collision support are enabled in Pinocchio. OpenMP and extra algorithms remain at their default OFF values.
- CI runs six functional checks and 32 selected upstream Python tests, then audits ELF symbol versions and dynamic dependencies, including NumPy's wheel libraries. No GLIBC symbol version requirement is allowed.
- Full Robot SDK/scene tests are not part of this upstream-library CI. During the local experiment, an R1 Pro bilateral-IK assertion failed identically with both the existing glibc build and the musl build; complete SDK integration remains a separate validation task.

Package versions observed during the build are recorded in logs. APK and transitive Python dependencies are not fully locked, so byte-for-byte reproducibility is not claimed. The standalone C++ dependencies and Python interpreter/NumPy remain dynamically linked to musl.
