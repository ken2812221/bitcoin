#!/usr/bin/env python3
import argparse
import hashlib
import os
import subprocess
import sys
import time
from subprocess import PIPE
from sys import stderr

GIT = os.getenv('GIT','git')

def tree_sha512sum(commit='HEAD'):
    # request metadata for entire tree, recursively
    files = []
    blob_by_name = {}
    for line in subprocess.check_output([GIT, 'ls-tree', '--full-tree', '-r', commit]).splitlines():
        name_sep = line.index(b'\t')
        metadata = line[:name_sep].split() # perms, 'blob', blobid
        assert(metadata[1] == b'blob')
        name = line[name_sep+1:]
        files.append(name)
        blob_by_name[name] = metadata[2]

    files.sort()
    # open connection to git-cat-file in batch mode to request data for all blobs
    # this is much faster than launching it per file
    p = subprocess.Popen([GIT, 'cat-file', '--batch'], stdout=PIPE, stdin=PIPE)
    overall = hashlib.sha512()
    for f in files:
        blob = blob_by_name[f]
        # request blob
        p.stdin.write(blob + b'\n')
        p.stdin.flush()
        # read header: blob, "blob", size
        reply = p.stdout.readline().split()
        assert(reply[0] == blob and reply[1] == b'blob')
        size = int(reply[2])
        # hash the blob data
        intern = hashlib.sha512()
        ptr = 0
        while ptr < size:
            bs = min(65536, size - ptr)
            piece = p.stdout.read(bs)
            if len(piece) == bs:
                intern.update(piece)
            else:
                raise IOError('Premature EOF reading git cat-file output')
            ptr += bs
        dig = intern.hexdigest()
        assert(p.stdout.read(1) == b'\n') # ignore LF that follows blob data
        # update overall hash with file hash
        overall.update(dig.encode("utf-8"))
        overall.update("  ".encode("utf-8"))
        overall.update(f)
        overall.update("\n".encode("utf-8"))
    p.stdin.close()
    if p.wait():
        raise IOError('Non-zero return value executing git cat-file')
    return overall.hexdigest()

def main():
    # get directory of this program
    dirname = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(usage='%(prog)s [options] [commit id]')
    parser.add_argument('--disable-tree-check', action='store_false', dest='verify_tree', help='disable SHA-512 tree check')
    parser.add_argument('--clean-merge', type=float, dest='clean_merge', default=float('inf'), help='Only check clean merge after <NUMBER> days ago (default: %(default)s)', metavar='NUMBER')
    (args, commit) = parser.parse_known_args()
    print("Using verify-commits data from " + dirname)
    verified_root = open(dirname + "/trusted-git-root", "r").read().splitlines()[0]
    verified_sha512_root = open(dirname + "/trusted-sha512-root-commit", "r").read().splitlines()[0]
    revsig_allowed = open(dirname + "/allow-revsig-commits", "r").read().splitlines()
    unclean_merge_allowed = open(dirname + "/allow-unclean-merge-commits", "r").read().splitlines()
    incorrect_sha512_allowed = open(dirname + "/allow-incorrect-sha512-commits", "r").read().splitlines()
    current_commit = "HEAD" if len(commit) == 0 else commit[0]
    if ' ' in current_commit:
        print("Commit must not contain spaces?", file=sys.stderr)
        exit(1)
    verify_tree = args.verify_tree
    no_sha1 = True
    prev_commit = ""
    initial_commit = current_commit
    branch = subprocess.check_output([GIT,'show','-s','--format=%H',initial_commit], universal_newlines=True).splitlines()[0]
    while True:
        if current_commit == verified_root:
            print('There is a valid path from "' + initial_commit + '" to ' + verified_root + ' where all commits are signed!')
            exit(0)
        if current_commit == verified_sha512_root:
            if verify_tree:
                print("All Tree-SHA512s matched up to " + verified_sha512_root, file=stderr)
            verify_tree = False
            no_sha1 = False
        os.environ['BITCOIN_VERIFY_COMMITS_ALLOW_SHA1'] = "0" if no_sha1 else "1"
        os.environ['BITCOIN_VERIFY_COMMITS_ALLOW_REVSIG'] = "1" if current_commit in revsig_allowed else "0"
        if subprocess.call([GIT, '-c', 'gpg.program=' + dirname + '/gpg.sh', 'verify-commit', current_commit], stdout=subprocess.DEVNULL):
            if prev_commit != "":
                print("No parent of " + prev_commit + " was signed with a trusted key!", file=sys.stderr)
                print("Parents are:", file=sys.stderr)
                parents = subprocess.check_output([GIT, 'show', '-s', '--format=format:%P', prev_commit], universal_newlines=True).splitlines()[0].split(' ')
                for parent in parents:
                    subprocess.call([GIT, 'show', '-s', parent], stdout=stderr)
            else:
                print(current_commit + " was not signed with a trusted key!", file=stderr)
            exit(1)
        if (verify_tree or prev_commit == "") and current_commit not in incorrect_sha512_allowed:
            tree_hash = tree_sha512sum(current_commit)
            if ("Tree-SHA512: "+tree_hash) not in subprocess.check_output([GIT, 'show', '-s', '--format=format:%B', current_commit], universal_newlines=True).splitlines():
                print("Tree-SHA512 did not match for commit " + current_commit, file=stderr)
                exit(1)
        parents = subprocess.check_output([GIT, 'show', '-s', '--format=format:%P', current_commit], universal_newlines=True).splitlines()[0].split(' ')
        commit_time = int(subprocess.check_output([GIT, 'show', '-s', '--format=format:%ct', current_commit], universal_newlines=True).splitlines()[0])
        check_merge = commit_time > time.time() - args.clean_merge * 24 * 60 * 60 # Only check commits in clean_merge days
        allow_unclean = current_commit in unclean_merge_allowed
        if len(parents) > 2:
            print("Commit " + current_commit + "is an octopus merge", file=stderr)
            exit(1)
        if len(parents) == 2 and check_merge and not allow_unclean:
            CURRENT_TREE=subprocess.check_output([GIT, 'show', '--format=%T', current_commit], universal_newlines=True).splitlines()[0]
            subprocess.call([GIT, 'checkout', '--force', '--quiet', parents[0]])
            subprocess.call([GIT, 'merge', '--no-ff', '--quiet', parents[1]], stdout=subprocess.DEVNULL)
            RECREATED_TREE = subprocess.check_output([GIT, 'show', '--format=format:%T', 'HEAD'], universal_newlines=True).splitlines()[0]
            if CURRENT_TREE != RECREATED_TREE:
                print("Merge commit " + current_commit + " is not clean", file=stderr)
                subprocess.call([GIT, 'diff', current_commit])
                subprocess.call([GIT, 'checkout', '--force', '--quiet', branch])
                exit(1)
            subprocess.call([GIT, 'checkout', '--force', '--quiet', branch])
        prev_commit = current_commit
        current_commit = parents[0]
if __name__ == '__main__':
    main()
