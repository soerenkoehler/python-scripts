#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen, PIPE
from os.path import exists


def parse_args():
    parser = ArgumentParser(description="ChDiff - a checksum based diff tool")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="dont print progress info")
    parser.add_argument("-f", "--force", action="store_true",
                        help="force recalculation of checksums (with --diff)")
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
                        help="the checksum method to use: sha256, sha512, md5")

    args = parser.parse_args()

    main_action_count = sum(
        map(lambda x: 1 if x else 0,
            [args.diff, args.create, args.verify]))

    if main_action_count != 1:
        parser.error(
            "Must specify exactly one of --diff, --create or --verify")

    return args


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


def process_directory(directory, function):
    path = Path(directory)
    progress("%s : " % path.resolve(), end='')
    function(path)
    progress("done")


def get_diff_output():
    dir1 = Path(ARGS.diff[0]).resolve()
    dir2 = Path(ARGS.diff[1]).resolve()
    create_checksum_for_diff(dir1)
    create_checksum_for_diff(dir2)
    return str(Popen(['diff', str(dir1 / SUM_FILE), str(dir2 / SUM_FILE)],
                     stdout=PIPE).communicate()[0], encoding='UTF-8')


def create_checksum_for_diff(path):
    if ARGS.force or is_out_of_date(path):
        process_directory(path, create_checksum)
    else:
        progress("%s : unchanged" % path.resolve())


def progress(text, end='\n'):
    if not ARGS.quiet:
        print(text, end=end, flush=True)


def is_out_of_date(path):
    if not exists(path / SUM_FILE):
        return True
    if Popen(['sh', '-c', '%s -cnewer "%s"' %
              (FIND_BASE, str(path / SUM_FILE))],
             cwd=path, stdout=PIPE).communicate()[0]:
        return True
    return False


def create_checksum(path):
    with open(path / SUM_FILE, "w") as out:
        Popen(['sh', '-c', '%s | sort | xargs -i %ssum -b {}' %
               (FIND_BASE, ARGS.method)],
              cwd=path, stdout=out).wait()


def verify_checksum(path):
    Popen(['%ssum' % ARGS.method, '-b', '-c',
           '--quiet', SUM_FILE], cwd=path).wait()


ARGS = parse_args()
SUM_FILE = 'chdiff.%s.txt' % ARGS.method
FIND_BASE = 'find -type f -not -path "./chdiff.*.txt"'

main()
