#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE


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


def process_directory(directory, function):
    path = Path(directory)
    print("--- %s" % path.resolve())
    function(path)


def create_checksum(path):
    with open(path / SUM_FILE, "w") as out:
        Popen(CMD_CREATE, cwd=path, stdout=out).wait()


def verify_checksum(path):
    Popen(CMD_VERIFY, cwd=path).wait()


def get_diff_output():
    dir1 = Path(ARGS.diff[0]).resolve()
    dir2 = Path(ARGS.diff[1]).resolve()
    process_directory(dir1, create_checksum)
    process_directory(dir2, create_checksum)
    return str(Popen(['diff',
                      str(dir1 / SUM_FILE),
                      str(dir2 / SUM_FILE)],
                     stdout=PIPE).communicate()[0], encoding='ASCII')


def main():
    if ARGS.create:
        for current_dir in ARGS.create:
            process_directory(current_dir, create_checksum)

    elif ARGS.verify:
        for current_dir in ARGS.verify:
            process_directory(current_dir, verify_checksum)

    elif ARGS.diff:
        diff = dict()
        for entry in [line.split(maxsplit=2)
                      for line in get_diff_output().splitlines()
                      if line[0] in ['<', '>']]:
            diff[entry[2]] = diff.get(entry[2], '') + entry[0]
        for key in sorted(diff.keys()):
            print("%s %s" % (key,
                             "new" if diff[key] == '>' else
                             "deleted" if diff[key] == '<'
                             else "modified"))


ARGS = parse_args()
SUM_FILE = "chdiff.%s.txt" % ARGS.method
CMD_CREATE = ['sh',
              '-c',
              'find -type f -not -path "./chdiff.*.txt" | sort | xargs -i %ssum {}' % ARGS.method]
CMD_VERIFY = ['%ssum' % ARGS.method, '-c', '--quiet', SUM_FILE]

main()
