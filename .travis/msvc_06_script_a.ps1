# Copyright (c) 2019 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

${ErrorActionPreference} = "Stop"

vcpkg install --triplet x64-windows-static  (${env:PACKAGES2} -Split ' ')
