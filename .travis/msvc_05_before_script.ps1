# Copyright (c) 2019 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

${ErrorActionPreference} = "Stop"

py build_msvc\msvc-autogen.py
${files} = (Get-ChildItem -Recurse | where {$_.extension -eq ".vcxproj"}).FullName
for (${i} = 0; ${i} -lt ${files}.length; ${i}++) {
    ${content} = (Get-Content ${files}[${i}]);
    ${content} = ${content}.Replace("</RuntimeLibrary>", "</RuntimeLibrary><DebugInformationFormat>None</DebugInformationFormat>");
    ${content} = ${content}.Replace("<WholeProgramOptimization>true", "<WholeProgramOptimization>false");
    Set-Content ${files}[${i}] ${content};
}

${conf_ini} = (Get-Content([IO.Path]::Combine(${env:TRAVIS_BUILD_DIR}, "test", "config.ini.in")))
${conf_ini} = ${conf_ini}.Replace("@abs_top_srcdir@", ${env:TRAVIS_BUILD_DIR})
${conf_ini} = ${conf_ini}.Replace("@abs_top_builddir@", ${env:TRAVIS_BUILD_DIR})
${conf_ini} = ${conf_ini}.Replace("@EXEEXT@", ".exe")
${conf_ini} = ${conf_ini}.Replace("@ENABLE_WALLET_TRUE@", "")
${conf_ini} = ${conf_ini}.Replace("@BUILD_BITCOIN_CLI_TRUE@", "")
${conf_ini} = ${conf_ini}.Replace("@BUILD_BITCOIND_TRUE@", "")
${conf_ini} = ${conf_ini}.Replace("@ENABLE_ZMQ_TRUE@", "")
${utf8} = New-Object Text.UTF8Encoding ${false}
[IO.File]::WriteAllLines([IO.Path]::Combine(${env:TRAVIS_BUILD_DIR}, "test", "config.ini"), ${conf_ini}, ${utf8})

vcpkg remove --outdated --recurse
vcpkg install --triplet x64-windows-static (${env:PACKAGES1} -Split ' ')
