# Copyright (c) 2019 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

${ErrorActionPreference} = "Stop"

msbuild /p:TrackFileAccess=false /p:CLToolExe=clcache build_msvc\bitcoin.sln /m /v:q /nologo
move "build_msvc\${env:PLATFORM}\${env:CONFIGURATION}\*.exe" src
src\test_bitcoin -k stdout -e stdout 2> NUL
src\bench_bitcoin -evals=1 -scaling=0 > NUL
py test\util\bitcoin-util-test.py
py test\util\rpcauth-test.py
py test\functional\test_runner.py --ci --quiet --combinedlogslen=4000 --failfast
