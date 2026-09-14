# pinocchio: reproducible platform builds

This guide describes the InsightOS fork/import and the scripts in this checkout.
The validated distribution from this repository is **Linux x86_64 musl**. glibc
and macOS source recipes below are native development builds, not a claim that
this fork publishes or has requalified those binaries. The complete installer
selects different binary formats and dependency locks for each platform.

## Source and tools

Validated musl tag: [`musl-v3.9.0-1`](https://github.com/insightos-community/pinocchio/releases/tag/musl-v3.9.0-1);
source commit: `2e5854965571237a17934e1baca13d856d053b3c`. Use a normal clone so container packaging can read `.git`.

```bash
git clone https://github.com/insightos-community/pinocchio.git pinocchio-repro
cd pinocchio-repro
git checkout --detach musl-v3.9.0-1
test "$(git rev-parse HEAD)" = 2e5854965571237a17934e1baca13d856d053b3c
```

Native build prerequisites: C++17 compiler, CMake >=3.22, Ninja, Eigen3 and Boost development packages. The native recipe below builds the C++ core only. Full Python, collision and URDF support additionally needs ABI-compatible Boost.Python, EigenPy, Coal, console_bridge, URDFDOM and OctoMap. The musl script builds this complete dependency prefix from the revisions in `ci/musl/dependencies.json`.

## Linux glibc

Run on a native Linux x86_64 glibc build host (Ubuntu 24.04 is the project CI
baseline). Install the prerequisites above. This native recipe uses the host
compiler and libraries; it does not apply the musl-only patches or emit a
portable/manylinux wheel.

```bash
git submodule update --init --recursive
cmake -S . -B build-glibc -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX="$PWD/prefix-glibc" -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=ON -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_INTERFACE=OFF -DBUILD_WITH_COLLISION_SUPPORT=OFF -DBUILD_WITH_URDF_SUPPORT=OFF
cmake --build build-glibc --parallel 2
ctest --test-dir build-glibc --output-on-failure --timeout 600
cmake --install build-glibc
```

## Linux musl: reproduce the Release

The authoritative pipeline is [musl-release.yml](.github/workflows/musl-release.yml),
with [build.sh](ci/musl/build.sh) as its local entry point. Run from the checked-out
repository root on a Linux x86_64 Docker host. Building requires network access
for pinned sources and package downloads; the output directory must be fresh.

```bash
REPRO_IMAGE='python:3.13-alpine3.23@sha256:75f27d686432419c9d42420b2b9ef605868c7a0682a6be10a6601fad46c2df01'
REPRO_WORK="$(mktemp -d "${TMPDIR:-/tmp}/pinocchio-musl.XXXXXXXX")"
docker run --rm --platform linux/amd64 --cpus=2 --memory=12g --memory-swap=12g --pids-limit=1024 \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=$REPRO_WORK,dst=/work" \
  "$REPRO_IMAGE" sh /src/ci/musl/build.sh
```

Outputs are in `$REPRO_WORK/dist/`; build/test logs and package inventories are
in `$REPRO_WORK/logs/`. Retain `build-manifest.json` and `SHA256SUMS` alongside:

- `pinocchio-3.9.0-cp313-musl-x86_64-prefix.tar.gz`

```bash
(cd "$REPRO_WORK/dist" && sha256sum -c SHA256SUMS)
```

Repository-local input/metadata manifests: [`dependencies.json`](ci/musl/dependencies.json).

The pinned Python/Alpine image does not freeze every subsequently installed APK
or pip package. Preserve the emitted package inventory; the result is a musl
build, not a completely static application or a bit-for-bit reproducibility claim.

## macOS / macosx

Use a fresh checkout on Apple Silicon, Xcode Command Line Tools and native arm64
versions of the prerequisites. Do not reuse Linux build directories or `$ORIGIN`
RPATHs. The following is a source-development recipe; it is not the macOS installer
release recipe or a universal/x86_64 qualification.

```bash
git submodule update --init --recursive
cmake -S . -B build-macos -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_INSTALL_PREFIX="$PWD/prefix-macos" -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=ON -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBUILD_TESTING=ON -DBUILD_EXAMPLES=OFF -DBUILD_PYTHON_INTERFACE=OFF -DBUILD_WITH_COLLISION_SUPPORT=OFF -DBUILD_WITH_URDF_SUPPORT=OFF
cmake --build build-macos --parallel 2
ctest --test-dir build-macos --output-on-failure --timeout 600
cmake --install build-macos
```

The installer uses `pin==3.9.0`, `libpinocchio`, EigenPy/Coal and cmeel wheels from the macOS installer lock, then repairs Mach-O search paths. It does not consume this musl prefix.

To reproduce the **complete macOS Python distribution** (including native wheels,
all dependency versions and load-path relocation), use the [installer recipe](https://github.com/insightos-community/quick-start/blob/main/artifacts/macos/README.md) and `artifacts/macos/installer-requirements.lock` in quick-start.

## Run the same build on GitHub

A manual dispatch builds/tests artifacts without publishing. Select the immutable
release tag to reproduce its scripts (GitHub CLI and workflow permission required):

```bash
gh workflow run musl-release.yml --repo insightos-community/pinocchio --ref musl-v3.9.0-1
gh run list --repo insightos-community/pinocchio --workflow musl-release.yml --limit 5
# Set REPRO_RUN_ID to the run ID printed above.
gh run watch "$REPRO_RUN_ID" --repo insightos-community/pinocchio --exit-status
gh run download "$REPRO_RUN_ID" --repo insightos-community/pinocchio --name musl-dist --dir downloaded-dist
```

## Reproduction evidence

Build in a fresh checkout and a separate output directory for each ABI. Preserve
source commits, compiler/tool versions, dependency locks, package inventories and
test logs. Fixed source revisions and a container digest reproduce the recipe;
unlocked OS packages, runner images, timestamps and build tools can still change
archive bytes. Compare a downloaded release against its published `SHA256SUMS`;
do not expect a local rebuild to have the same digest.

See the [complete installer and repository index](https://github.com/insightos-community/quick-start/blob/main/README.build.md) for assembly order,
platform locks and end-to-end validation. Local build commands do not publish a
Release. Publishing requires repository write access and a new version tag;
existing release tags/assets should not be replaced.

## Windows x64

The native Windows component preview is `windows-v3.9.0-preview.1`. It provides
CPython 3.13 / NumPy 2.3.5 wheels with URDF and collision support and records
compilation and standalone verification revisions separately. See
[the Windows recipe](ci/windows/README.md) for the locked dependency inputs and
verification scope. In an x64 Visual Studio developer PowerShell with Miniconda
and uv 0.12.12, use a fresh checkout and empty build/output directories:

```powershell
git checkout windows-v3.9.0-preview.1
$env:GITHUB_WORKSPACE = (Get-Location).Path
$env:RUNNER_TEMP = Join-Path $env:TEMP 'semantic-pinocchio-windows-build'
New-Item -ItemType Directory -Force $env:RUNNER_TEMP | Out-Null
./ci/windows/build.ps1
```
