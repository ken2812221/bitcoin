#!/usr/bin/env python3
# Copyright (c) 2019 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import argparse
import json
import sys

def command(args):
    if args.invalid:
        sys.stdout.write("{")
    elif args.success:
        sys.stdout.write(json.dumps({"success": True}))
    elif args.fail:
        sys.stdout.write(json.dumps({"success": False, "error": "reason"}))
    else:
        raise RuntimeError("Missing arguments")


parser = argparse.ArgumentParser(prog='./mock_command.py', description='Test runCommandParseJSON() via runcommand RPC')
parser.add_argument('--success', action='store_true', help='Respond with {success: true}')
parser.add_argument('--fail', action='store_true', help='Respond with {success: false, error: "reason"}')
parser.add_argument('--invalid', action='store_true', help='Return malformed JSON')
parser.set_defaults(func=command)

if len(sys.argv) == 1:
    args = parser.parse_args(['-h'])
    exit()

args_parser = parser.parse_args()
args_parser.func(args_parser)
