$ErrorActionPreference = 'Stop'
$prefix = Join-Path $env:RUNNER_TEMP 'pinocchio-build-env'
$stage = Join-Path $env:RUNNER_TEMP 'pinocchio-installed'
$build = Join-Path $env:RUNNER_TEMP 'pinocchio-build'
$dist = Join-Path $env:GITHUB_WORKSPACE 'dist'
conda create --yes --prefix $prefix --file ci/windows/conda-explicit.txt
if ($LASTEXITCODE -ne 0) { throw 'Conda build environment failed' }
$env:PATH = "$prefix;$prefix/Library/bin;$prefix/Scripts;$env:PATH"
$python = Join-Path $prefix 'python.exe'
& $python -c "import numpy, eigenpy, coal; assert numpy.__version__ == '2.3.5'"
if ($LASTEXITCODE -ne 0) { throw 'Build dependency imports failed' }
cmake -S . -B $build -G Ninja "-DCMAKE_PREFIX_PATH=$prefix/Library" "-DCMAKE_INSTALL_PREFIX=$stage" "-DPYTHON_EXECUTABLE=$python" "-DPYTHON_SITELIB=$stage/Lib/site-packages" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DBUILD_BENCHMARK=OFF -DBUILD_PYTHON_INTERFACE=ON -DBUILD_WITH_URDF_SUPPORT=ON -DBUILD_WITH_COLLISION_SUPPORT=ON -DBUILD_WITH_EXTRA_SUPPORT=OFF -DBUILD_WITH_OPENMP_SUPPORT=OFF -DGENERATE_PYTHON_STUBS=OFF '-DCMAKE_CXX_FLAGS=/bigobj /EHsc'
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
cmake --build $build --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Pinocchio compilation failed' }
cmake --install $build
if ($LASTEXITCODE -ne 0) { throw 'Pinocchio staging failed' }
& $python ci/windows/package.py $prefix $stage $dist
if ($LASTEXITCODE -ne 0) { throw 'Wheel packaging failed' }
& $python -m pip download --only-binary=:all: --no-deps --dest $dist numpy==2.3.5
if ($LASTEXITCODE -ne 0) { throw 'NumPy wheel download failed' }
$env:UV_PYTHON_INSTALL_DIR = Join-Path $env:RUNNER_TEMP 'standalone-python'
uv python install 3.13.15
if ($LASTEXITCODE -ne 0) { throw 'Standalone Python download failed' }
$standalone = (uv python find --managed-python 3.13.15).Trim()
$verify = Join-Path $env:RUNNER_TEMP 'clean-verify'
uv venv --python $standalone $verify
if ($LASTEXITCODE -ne 0) { throw 'Standalone venv failed' }
$verifyPython = Join-Path $verify 'Scripts/python.exe'
uv pip install --python $verifyPython --no-index --find-links $dist pin==3.9.0
if ($LASTEXITCODE -ne 0) { throw 'Offline wheel installation failed' }
uv pip check --python $verifyPython
if ($LASTEXITCODE -ne 0) { throw 'Offline dependency check failed' }
# Make hardcoded build-prefix dependencies fail, including DLL lookup outside PATH.
$env:PATH = "$(Split-Path $standalone);$env:SystemRoot/System32;$env:SystemRoot"
$env:PYTHONPATH = ''
$env:PYTHONNOUSERSITE = '1'
Rename-Item $prefix "$prefix-unavailable"
& $verifyPython ci/windows/verify.py "$dist/windows-validation.json"
if ($LASTEXITCODE -ne 0) { throw 'Standalone validation failed' }
Copy-Item ci/windows/conda-lock.json $dist
Copy-Item ci/windows/conda-explicit.txt $dist
Get-ChildItem $dist -File | Sort-Object Name | ForEach-Object { "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)" } | Set-Content -Encoding ascii "$dist/SHA256SUMS"
