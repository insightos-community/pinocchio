# Windows x64 / CPython 3.13

This recipe builds Pinocchio 3.9.0 from this checkout with MSVC. It packages
locked conda-forge EigenPy 3.12.0, Coal 3.0.2 and their native dependencies into
private-DLL wheels. Those dependencies are pinned binary inputs, not rebuilt
from source by this workflow. Conda is a build tool; the validation environment
uses a separate standalone CPython 3.13.15 and NumPy 2.3.5.

The locked EigenPy headers gate MSVC pragmas on the non-predefined `WIN32`
spelling and stringize a token argument to `__pragma`. `patch_eigenpy.py`
corrects those two build-header spellings; it checks the expected original text
and leaves the binary dependency intact. A native syntax-only header preflight
exercises both deprecated-file and allocator macros before the full build.

Use an x64 Visual Studio 2022 developer PowerShell with Miniconda and uv 0.12.12
on PATH. Start from a fresh checkout and empty temporary/output directories:

```powershell
$env:GITHUB_WORKSPACE = (Get-Location).Path
$env:RUNNER_TEMP = Join-Path $env:TEMP 'semantic-pinocchio-windows-build'
New-Item -ItemType Directory -Force $env:RUNNER_TEMP | Out-Null
./ci/windows/build.ps1
```

`build.ps1` initializes the pinned CMake submodule, installs the explicit build
lock, builds Pinocchio with URDF and collision support, packages wheels, and
installs them offline into a standalone Python venv. It hides the original
Conda prefix and removes its PATH entries before checking FK/RNEA, URDF,
mesh loading, collision queries and loaded DLL paths. Validation evidence and
`SHA256SUMS` are written into `dist/` only after all checks pass.

The dependency records in `conda-lock.json` contain exact download URLs, SHA-256
and MD5; Conda consumes the MD5-pinned `conda-explicit.txt`. The shared native
wheel includes dependency metadata and available license texts. Python runtime
DLLs are excluded so that the package uses the installed base interpreter.

The [workflow](../../.github/workflows/windows-release.yml) runs on
`windows-2022`. Successful branch builds upload an Actions artifact. A
`windows-v3.9.0-*` tag creates a prerelease only after build and standalone
verification succeed. This component does not qualify the Semantic installer
or GPU rendering; use the validation report for the exact tested scope.

If compilation succeeded but a verification-only check needs correction, dispatch
the workflow with `artifact_run_id` set to that completed push run. Revalidation
rejects any change outside the verifier, its workflow/README and revalidation
script, records both the actual build revision and verifier revision, and installs
the original wheels offline into a fresh standalone Python. NumPy's own
`numpy.libs` CRT is an allowed bundled dependency; runner-global CRTs remain rejected.

The optional `publish_tag` dispatch input publishes these revalidated wheels as
a Windows prerelease. The release records the original compilation revision and
the separate verification revision. Published matching releases are preserved
on retry; an existing release with different provenance is rejected.
