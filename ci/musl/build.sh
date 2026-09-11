#!/bin/sh
set -eu
cd /work
mkdir -p logs build prefix downloads dist
exec >logs/build.log 2>&1
date -u
apk add --no-cache build-base cmake ninja git curl linux-headers eigen-dev assimp-dev qhull-dev qhull-static tinyxml2-dev zlib-dev pkgconf binutils file patch
git config --global --add safe.directory '*'
export PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
python -m pip install --only-binary=:all: numpy==2.3.5 pytest==8.3.5
apk info -v > logs/apk-packages.txt
python -m pip freeze > logs/python-packages.txt
cp -a /src /work/pinocchio
git -C pinocchio submodule update --init --depth 1 cmake
python /src/ci/musl/fetch_dependencies.py
export CMAKE_PREFIX_PATH=/work/prefix
export LD_LIBRARY_PATH=/work/prefix/lib
export PYTHONPATH=/work/prefix/lib/python3.13/site-packages
export PKG_CONFIG_PATH=/work/prefix/lib/pkgconfig
curl -fsSL --retry 3 https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2 -o downloads/boost_1_89_0.tar.bz2
echo '85a33fa22621b4f314f8e85e1a5e2a9363d22e4f4992925d4bb3bc631b5a0c7a  downloads/boost_1_89_0.tar.bz2' | sha256sum -c -
tar -xjf downloads/boost_1_89_0.tar.bz2 -C build
(cd build/boost_1_89_0
 ./bootstrap.sh --prefix=/work/prefix --with-python=/usr/local/bin/python3 --with-libraries=filesystem,serialization,python,system > /work/logs/boost-configure.log 2>&1
 ./b2 -j2 variant=release link=shared threading=multi cxxstd=17 install > /work/logs/boost-build.log 2>&1)
build_project() {
  project_name=$1
  shift
  date -u
  echo "Building $project_name"
  cmake -S "$project_name" -B "build/$project_name" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG' \
    -DCMAKE_INSTALL_PREFIX=/work/prefix -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_INSTALL_RPATH=/work/prefix/lib \
    -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF -DINSTALL_DOCUMENTATION=OFF \
    -DPYTHON_EXECUTABLE=/usr/local/bin/python3 -DPython_EXECUTABLE=/usr/local/bin/python3 \
    "$@" > "logs/$project_name-configure.log" 2>&1
  cmake --build "build/$project_name" --parallel 2 > "logs/$project_name-build.log" 2>&1
  cmake --install "build/$project_name" > "logs/$project_name-install.log" 2>&1
}
build_project console_bridge
build_project urdfdom_headers
build_project urdfdom
build_project octomap -DBUILD_OCTOVIS_SUBPROJECT=OFF -DBUILD_DYNAMICETD3D_SUBPROJECT=OFF
build_project eigenpy -DBUILD_PYTHON_INTERFACE=ON -DGENERATE_PYTHON_STUBS=OFF -DBUILD_TESTING_SCIPY=OFF
build_project coal -DBUILD_PYTHON_INTERFACE=ON -DCOAL_HAS_QHULL=ON -DCOAL_BACKWARD_COMPATIBILITY_WITH_HPP_FCL=ON -DGENERATE_PYTHON_STUBS=OFF
build_project pinocchio -DBUILD_PYTHON_INTERFACE=ON -DBUILD_WITH_COLLISION_SUPPORT=ON -DBUILD_WITH_URDF_SUPPORT=ON -DGENERATE_PYTHON_STUBS=OFF
python -m pytest -p no:cacheprovider -q /src/ci/musl/test_runtime.py > logs/smoke-tests.log 2>&1
python -m pytest -p no:cacheprovider -q \
  pinocchio/unittest/python/bindings_kinematics.py \
  pinocchio/unittest/python/bindings_dynamics.py \
  pinocchio/unittest/python/bindings_aba.py \
  pinocchio/unittest/python/bindings_rnea.py \
  pinocchio/unittest/python/bindings_geometry_model.py \
  pinocchio/unittest/python/bindings_geometry_object.py \
  pinocchio/unittest/python/bindings_joint_algorithms.py > logs/upstream-tests.log 2>&1
python /src/ci/musl/audit_elf.py > logs/elf-audit-summary.log 2>&1
python /src/ci/musl/package.py
date -u
echo BUILD_AND_TEST_COMPLETE
