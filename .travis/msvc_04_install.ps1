# Copyright (c) 2019 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

${ErrorActionPreference} = "Stop"

choco install python3
refreshenv
py -m pip install clcache

git clone https://github.com/Microsoft/vcpkg.git ${env:VCPKGPATH}
move "${env:HOME}/vcpkg_installed" "${env:VCPKGPATH}/installed"

# Building release packages only instead of building both debug and release
[IO.File]::AppendAllText("${env:VCPKGPATH}\triplets\x64-windows-static.cmake", "set(VCPKG_BUILD_TYPE release)`n")

bootstrap-vcpkg.bat
vcpkg integrate install
