#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from datetime import datetime
from filecmp import dircmp
from fnmatch import fnmatchcase
from os import remove, replace, stat
from pathlib import Path
from subprocess import PIPE, Popen


def parse_args():
    parser = ArgumentParser(description="ChDiff - a checksum based diff tool")

    parser.add_argument("-q", "--quiet", action="store_true",
                        help="dont print log messages")
    parser.add_argument("-m", "--method", action="store", default="sha256",
                        choices=["sha256", "sha512", "md5", "size"],
                        help="the checksum method to use")

    cmd_group = parser.add_mutually_exclusive_group(required=True)
    cmd_group.add_argument("--diff", action="store", nargs=2,
                           metavar=("DIR1", "DIR2"),
                           help="compute difference between DIR1 and DIR2")
    cmd_group.add_argument("--sync", action="store", nargs=2,
                           metavar=("SRC", "DST"),
                           help="sync SRC into DST (new, modified and deleted files)")
    cmd_group.add_argument("--backup", action="store", nargs=2,
                           metavar=("SRC", "DST"),
                           help="backup SRC into DST (new and modified files only)")
    cmd_group.add_argument("--create", action="store", nargs='+',
                           metavar="DIR",
                           help="compute checksums for given DIRs")
    cmd_group.add_argument("--verify", action="store", nargs='+',
                           metavar="DIR",
                           help="verify checksums for given DIRs")

    args = parser.parse_args()

    return args


def main():
    if ARGS.create:
        for current_dir in ARGS.create:
            process_directory(current_dir, create_checksum)

    elif ARGS.verify:
        for current_dir in ARGS.verify:
            process_directory(current_dir, verify_checksum)

    elif ARGS.diff:
        dir1 = Path(ARGS.diff[0]).resolve()
        dir2 = Path(ARGS.diff[1]).resolve()
        report_diff(get_checksum_diff(dir1, dir2, SUM_FILE, SUM_FILE))

    elif ARGS.sync:
        pass

    elif ARGS.backup:
        pass


def process_directory(directory, function):
    path = Path(directory)
    log("scanning : %s" % path.resolve())
    function(path)
    log("finished : %s" % path.resolve())


def get_checksum_diff(dir1, dir2, sumfile1, sumfile2):
    process_directory(dir1, create_checksum)
    process_directory(dir2, create_checksum)
    diff = dict()
    for (change, path) in [line.split(maxsplit=2,
                                      sep=SEPARATORS[ARGS.method])
                           for line in str(Popen(['diff',
                                                  str(dir1 / sumfile1),
                                                  str(dir2 / sumfile2)],
                                                 stdout=PIPE).communicate()[0],
                                           encoding='UTF-8').splitlines()
                           if line[0] in ['<', '>']]:
        normalized_path = Path(path)
        if normalized_path in diff:
            diff[normalized_path] = '* *'
        else:
            diff[normalized_path] = '< +' if change[0] == '>' else '> -'
    for (path, change) in get_timestamp_diff(Path("."), dircmp(dir1, dir2)).items():
        if path in diff:
            diff[path] = change[0:2] + "*"
        else:
            diff[path] = change
    return diff


def create_checksum(path):
    create_tmp_checksum(path)
    replace(path / TMP_FILE, path / SUM_FILE)


def verify_checksum(path):
    create_tmp_checksum(path)
    report_diff(get_checksum_diff(path, path, SUM_FILE, TMP_FILE),
                path.resolve())
    remove(path / TMP_FILE)


def create_tmp_checksum(path):
    with open(path / TMP_FILE, "w") as out:
        Popen(['sh', '-c', '%s | sort | xargs -i %s "{}"' %
               (FIND_BASE, METHODS[ARGS.method])],
              cwd=path, stdout=out).wait()


def get_timestamp_diff(prefix, current_dir):
    result = dict()
    for file in current_dir.common_files:
        if not fnmatchcase(file, EXCLUDE_PATTERN):
            time_a = stat(Path(current_dir.left) / file).st_mtime
            time_b = stat(Path(current_dir.right) / file).st_mtime
            if time_a != time_b:
                print("%s %s %s" % (prefix / file, time_a, time_b))
                result[prefix / file] = "< =" if time_a < time_b else "> ="
    for directory in current_dir.subdirs.items():
        result.update(get_timestamp_diff(prefix / directory[0], directory[1]))
    return result


def report_diff(diff, parent=Path()):
    for path in sorted(diff.keys()):
        print("%s %s" % (diff[path], parent / path))


def log(text):
    if not ARGS.quiet:
        now = datetime.now().replace(microsecond=0).isoformat()
        print("[%s] %s" % (now, text), flush=True)


ARGS = parse_args()

SUM_FILE = 'chdiff.%s.txt' % ARGS.method
TMP_FILE = 'chdiff.%s.tmp' % ARGS.method
EXCLUDE_PATTERN = 'chdiff.*.t??'
FIND_BASE = 'find -type f -not -name "%s"' % EXCLUDE_PATTERN

METHODS = {
    "sha256": "sha256sum -b",
    "sha512": "sha512sum -b",
    "md5": "md5sum -b",
    "size": "wc -c",
}

SEPARATORS = {
    "sha256": " *./",
    "sha512": " *./",
    "md5": " *./",
    "size": " ./",
}

if __name__ == '__main__':
    main()
