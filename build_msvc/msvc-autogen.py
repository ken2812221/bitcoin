#!/usr/bin/env python3

import argparse
import re
import os
import shutil

SOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
MSVC_DIR = os.path.abspath(os.path.dirname(__file__))

libs = [
    'libbitcoin_cli',
    'libbitcoin_common',
    'libbitcoin_crypto',
    'libbitcoin_server',
    'libbitcoin_util',
    'libbitcoin_wallet_tool',
    'libbitcoin_wallet',
    'libbitcoin_zmq',
]

ignore_list = [
]

lib_sources = {}


def parse_makefile(makefile):
    with open(makefile, 'r', encoding='utf-8') as file:
        current_lib = ''
        for line in file.read().splitlines():
            if current_lib:
                source = line.split()[0]
                if source.endswith('.cpp') and not source.startswith('$') and source not in ignore_list:
                    source_filename = source.replace('/', '\\')
                    object_filename = source.replace('/', '_')[:-4] + ".obj"
                    lib_sources[current_lib].append((source_filename, object_filename))
                if not line.endswith('\\'):
                    current_lib = ''
                continue
            for lib in libs:
                _lib = lib.replace('-', '_')
                if re.search(_lib + '.*_SOURCES \\= \\\\', line):
                    current_lib = lib
                    lib_sources[current_lib] = []
                    break

def set_custom_paths(qtDir, protocPath):
    with open(os.path.join(MSVC_DIR, 'Directory.Build.props.in'), 'r', encoding='utf-8') as rfile:
        s = rfile.read()
        if qtDir:
            s = s.replace("@QtBaseDir@", qtDir)
        if protocPath:
            s = s.replace("@ProtocPath@", protocPath)
    with open(os.path.join(MSVC_DIR, 'Directory.Build.props'), 'w', encoding='utf-8',newline='\n') as wfile:
        wfile.write(s)

def main():
    parser = argparse.ArgumentParser(description='Bitcoin-core msbuild configuration initialiser.')
    parser.add_argument('-qtdir', nargs='?',help='Optionally sets the directory to use for the static '
        'Qt5 binaries and include files, default is C:\Qt5.9.7_ssl_x64_static_vs2017.')
    parser.add_argument('-protocpath', nargs='?',help='Optionally sets the path for the Protobuf compiler,'
         ' default is C:\Tools\vcpkg\installed\x64-windows-static\tools\protobuf\protoc.exe.')
    args = parser.parse_args()
    if args.qtdir or args.protocpath:
        set_custom_paths(args.qtdir, args.protocpath)

    for makefile_name in os.listdir(SOURCE_DIR):
        if 'Makefile' in makefile_name:
            parse_makefile(os.path.join(SOURCE_DIR, makefile_name))
    for key, value in lib_sources.items():
        vcxproj_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), key, key + '.vcxproj'))
        content = ''
        for source_filename, object_filename in value:
            content += '    <ClCompile Include="..\\..\\src\\' + source_filename + '">\n'
            content += '      <ObjectFileName>$(IntDir)' + object_filename + '</ObjectFileName>\n'
            content += '    </ClCompile>\n'
        with open(vcxproj_filename + '.in', 'r', encoding='utf-8') as vcxproj_in_file:
            with open(vcxproj_filename, 'w', encoding='utf-8') as vcxproj_file:
                vcxproj_file.write(vcxproj_in_file.read().replace(
                    '@SOURCE_FILES@\n', content))
    shutil.copyfile(os.path.join(MSVC_DIR, 'bitcoin_config.h'), os.path.join(SOURCE_DIR, 'config\\bitcoin-config.h'))
    shutil.copyfile(os.path.join(MSVC_DIR, 'libsecp256k1_config.h'), os.path.join(SOURCE_DIR, 'secp256k1\\src\\libsecp256k1-config.h'))
    shutil.copyfile(os.path.join(MSVC_DIR, 'bitcoin.sln.in'), os.path.join(MSVC_DIR, 'bitcoin.sln'))

if __name__ == '__main__':
    main()
