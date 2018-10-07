#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen


def parse_args():
    parser = ArgumentParser(description="ChDiff - a checksum based diff tool")
    parser.add_argument("-d", "--diff", action="store", nargs=2,
                        metavar=("DIR1", "DIR2"),
                        help="compute difference between DIR1 and DIR2")
    parser.add_argument("-c", "--create", action="store", nargs='+',
                        metavar="DIR",
                        help="compute checksums for given DIRs")
    parser.add_argument("-v", "--verify", action="store", nargs='+',
                        metavar="DIR",
                        help="verify checksums for given DIRs")
    parser.add_argument("-m", "--method", action="store", default="sha256",
                        help="the checksum method to use")

    args = parser.parse_args()

    main_action_count = sum(
        map(lambda x: 1 if x else 0,
            [args.diff, args.create, args.verify]))

    if main_action_count != 1:
        parser.error(
            "Must specify exactly one of --diff, --create or --verify")

    return args


def create_checksums():
    cmd = ['sh',
           '-c',
           'find -type f -not -path "./chdiff.*.txt" | sort | xargs -i %ssum {}' % ARGS.method]
    for directory in ARGS.create:
        path = Path(directory)
        print(path.resolve())
        with open(path / SUM_FILE, "w") as out:
            Popen(cmd, cwd=path, stdout=out).wait()


def verify_checksums():
    cmd = ['%ssum' % ARGS.method, '-c', '--quiet', SUM_FILE]
    for directory in ARGS.verify:
        path = Path(directory)
        print(path.resolve())
        Popen(cmd, cwd=path).wait()


ARGS = parse_args()
SUM_FILE = "chdiff.%s.txt" % ARGS.method

if ARGS.create:
    create_checksums()

if ARGS.verify:
    verify_checksums()
