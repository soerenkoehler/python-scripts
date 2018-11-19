#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from datetime import datetime
from filecmp import dircmp
from fnmatch import fnmatchcase
from hashlib import md5, sha256, sha512
from os import stat, walk
from pathlib import Path
from sys import stdout


def parse_args():
    parser = ArgumentParser(description="ChDiff - a checksum based diff tool")

    parser.add_argument("-q", "--quiet", action="store_true",
                        help="dont print log messages")
    parser.add_argument("-m", "--method", action="store", default="sha256",
                        choices=["sha256", "sha512", "md5", "size"],
                        help="the checksum method to use")
    parser.add_argument("--full", action="store_true",
                        help="show also files with equal checksum but different timestamps")

    cmd_group = parser.add_mutually_exclusive_group(required=True)
    cmd_group.add_argument("-d", "--diff", action="store", nargs=2,
                           metavar=("DIR1", "DIR2"),
                           help="compute difference between DIR1 and DIR2")
    cmd_group.add_argument("-s", "--sync", action="store", nargs=2,
                           metavar=("SRC", "DST"),
                           help="sync SRC into DST (new, modified and deleted files)")
    cmd_group.add_argument("-b", "--backup", action="store", nargs=2,
                           metavar=("SRC", "DST"),
                           help="backup SRC into DST (new and modified files only)")
    cmd_group.add_argument("-c", "--create", action="store", nargs='+',
                           metavar="DIR",
                           help="compute checksums for given DIRs")
    cmd_group.add_argument("-v", "--verify", action="store", nargs='+',
                           metavar="DIR",
                           help="verify checksums for given DIRs")

    args = parser.parse_args()

    return args


def main():
    if ARGS.create:
        process_directories(ARGS.create, create_checksum)

    elif ARGS.verify:
        process_directories(ARGS.verify, verify_checksum)

    elif ARGS.diff:
        report_diff(get_diff(Path(ARGS.diff[0]).resolve(),
                             Path(ARGS.diff[1]).resolve()))

    elif ARGS.sync:
        pass

    elif ARGS.backup:
        pass


def get_diff(dir1, dir2):
    if process_directories([dir1, dir2], create_checksum):
        diff = get_checksum_diff(load_checksums(dir1), load_checksums(dir2))
        for (path, change) in get_timestamp_diff(Path("."), dircmp(dir1, dir2)).items():
            if ARGS.full:
                diff[path] = change + (diff[path] if path in diff else [])
            elif path in diff:
                diff[path] = change
        return diff
    return {}


def process_directories(directories, function):
    result = True
    for path in [Path(d) for d in directories]:
        try:
            log("scanning", path)
            log(function(path), path / SUM_FILE)
        except FileNotFoundError as file_not_found:
            log("file not found", path / file_not_found.filename)
            result = False
    return result


def create_checksum(path):
    checksums = calculate_checksums(path)
    with open(path / SUM_FILE, "w", encoding="utf-8") as out:
        out.write("\n".join(
            ["%s *./%s" % (checksums[f], f) for f in sorted(checksums)]))
    return "created"


def verify_checksum(path):
    diff = get_checksum_diff(load_checksums(path), calculate_checksums(path))
    report_diff(diff, path.resolve())
    return "%s difference(s) found" % len(diff) if diff else "OK"


def get_checksum_diff(source, target):
    diff = {}
    for file in [f for f in source if f in target]:
        if target[file] != source[file]:
            diff[file] = TARGET_MODIFIED
    for file in [f for f in source if f not in target]:
        diff[file] = TARGET_MISSING
    for file in [f for f in target if f not in source]:
        diff[file] = SOURCE_MISSING
    return diff


def calculate_checksums(path):
    checksums = {}
    for (current, _, files) in walk(path):
        for file in [Path(current) / f
                     for f in files
                     if not fnmatchcase(f, EXCLUDE_PATTERN)]:
            checksums[str(file.relative_to(path))] = METHODS[ARGS.method](file)
    return checksums


def load_checksums(path):
    checksums = {}
    with open(path / SUM_FILE, "r", encoding="utf-8") as infile:
        for (checksum, file) in [line.rstrip().split(maxsplit=2, sep=" *./")
                                 for line in infile.readlines()]:
            checksums[str(Path(file))] = checksum
    return checksums


def get_timestamp_diff(prefix, current_dir):
    result = {}
    for file in current_dir.common_files:
        if not fnmatchcase(file, EXCLUDE_PATTERN):
            time_a = stat(Path(current_dir.left) / file).st_mtime
            time_b = stat(Path(current_dir.right) / file).st_mtime
            if time_a != time_b:
                result[str(prefix / file)] = [TARGET_NEWER if time_a < time_b
                                              else TARGET_OLDER]
    for directory in current_dir.subdirs.items():
        result.update(get_timestamp_diff(prefix / directory[0], directory[1]))
    return result


def report_diff(diff, parent=Path()):
    for path in sorted(diff.keys()):
        print("{:<2} {}".format("".join(diff[path]),
                                path_to_str(parent / path)))


def log(text, path=None):
    if not ARGS.quiet:
        if path:
            text = "%s : %s" % (text, path_to_str(path.resolve()))
        now = datetime.now().replace(microsecond=0).isoformat()
        print("[{}] {}".format(now, text), flush=True)


def path_to_str(path):
    return bytes(path).decode(stdout.encoding)


def method_sha256(file):
    return calculate_digest(file, sha256())


def method_sha512(file):
    return calculate_digest(file, sha512())


def method_md5(file):
    return calculate_digest(file, md5())


def calculate_digest(file, digest):
    with open(file, "rb") as infile:
        digest.update(infile.read())
    return digest.hexdigest()


def method_size(file):
    return str(stat(file).st_size)


ARGS = parse_args()

SUM_FILE = 'chdiff.%s.txt' % ARGS.method
EXCLUDE_PATTERN = 'chdiff.*.txt'

METHODS = {
    "sha256": method_sha256,
    "sha512": method_sha512,
    "md5": method_md5,
    "size": method_size,
}

TARGET_MODIFIED = "*"
TARGET_NEWER = "<"
TARGET_OLDER = ">"
TARGET_MISSING = "-"
SOURCE_MISSING = "+"

if __name__ == '__main__':
    main()
