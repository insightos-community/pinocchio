# Reuse compiled wheels only when every non-verification source file is identical.
param([Parameter(Mandatory=$true)][long]$RunId)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$verificationCommit = (git rev-parse HEAD).Trim()
$run = gh api "repos/$env:GITHUB_REPOSITORY/actions/runs/$RunId" | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $run.status -ne 'completed' -or $run.event -ne 'push' -or $run.path -ne '.github/workflows/windows-release.yml') { throw 'Untrusted native build run' }
$buildCommit = $run.head_sha
if ($buildCommit -notmatch '^[0-9a-f]{40}$') { throw 'Invalid build revision' }
git fetch --no-tags --depth=1 origin $buildCommit
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect original build source' }
$changed = @(git diff --name-only $buildCommit HEAD)
if ($LASTEXITCODE -ne 0) { throw 'Source comparison failed' }
$allowed = @('ci/windows/verify.py','ci/windows/revalidate.ps1','ci/windows/README.md','.github/workflows/windows-release.yml')
foreach ($file in $changed) { if ($file -notin $allowed) { throw "Compiled input changed: $file" } }
$inputDirectory = Join-Path $env:RUNNER_TEMP 'original-native-artifact'
gh run download $RunId --repo $env:GITHUB_REPOSITORY --name pinocchio-windows-cp313 --dir $inputDirectory
if ($LASTEXITCODE -ne 0) { throw 'Original artifact download failed' }
$dist = Join-Path $env:GITHUB_WORKSPACE 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null
$wheels = @(Get-ChildItem $inputDirectory -Recurse -Filter '*.whl')
if ($wheels.Count -ne 5) { throw 'Expected four native wheels and NumPy' }
foreach ($wheel in $wheels) { Copy-Item $wheel.FullName $dist }
uv python install 3.13.15
if ($LASTEXITCODE -ne 0) { throw 'Standalone Python download failed' }
$standalone = (uv python find --managed-python 3.13.15).Trim()
$verify = Join-Path $env:RUNNER_TEMP 'revalidate-native'
uv venv --python $standalone $verify
if ($LASTEXITCODE -ne 0) { throw 'Standalone venv failed' }
$python = Join-Path $verify 'Scripts/python.exe'
uv pip install --python $python --no-index --find-links $dist pin==3.9.0
if ($LASTEXITCODE -ne 0) { throw 'Offline wheel installation failed' }
uv pip check --python $python
if ($LASTEXITCODE -ne 0) { throw 'Offline dependency check failed' }
$env:PATH = "$(Split-Path $standalone);$env:SystemRoot/System32;$env:SystemRoot"
$env:PYTHONPATH = ''
$env:PYTHONNOUSERSITE = '1'
$env:SEMANTIC_PINOCCHIO_SOURCE_COMMIT = $buildCommit
$env:SEMANTIC_PINOCCHIO_VERIFICATION_COMMIT = $verificationCommit
& $python ci/windows/verify.py "$dist/windows-validation.json"
if ($LASTEXITCODE -ne 0) { throw 'Standalone validation failed' }
Copy-Item ci/windows/conda-lock.json $dist
Copy-Item ci/windows/conda-explicit.txt $dist
@{ build_run=$RunId; build_commit=$buildCommit; verification_commit=$verificationCommit; changed_verification_files=$changed } | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 "$dist/revalidation.json"
Get-ChildItem $dist -File | Sort-Object Name | ForEach-Object { "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)" } | Set-Content -Encoding ascii "$dist/SHA256SUMS"
