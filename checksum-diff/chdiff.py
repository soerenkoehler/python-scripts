#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser, Namespace
from datetime import datetime
from filecmp import dircmp
from fnmatch import fnmatchcase
from hashlib import md5, sha256, sha512
from os import stat, walk, listdir, makedirs
from pathlib import Path
from sys import stdout, stderr
from time import sleep


def parse_args():
    parser = ArgumentParser(description="ChDiff - a checksum based diff tool",
                            epilog="Global options must precede sub-commands.")

    parser.add_argument("-q", "--quiet", action="store_true",
                        help="dont print log messages")
    parser.add_argument("-m", "--method", action="store", default="sha256",
                        choices=["sha256", "sha512", "md5", "size"],
                        help="the checksum method to use")

    subparsers = parser.add_subparsers(
        title="commands",
        help="use '%(prog)s CMD -h' for additional help")
    diff = subparsers.add_parser("diff", aliases=["d"],
                                 help="compute difference between two directories")
    diff.add_argument("left", type=Path, action="store", metavar="LEFT",
                      help="first directory to compare")
    diff.add_argument("right", type=Path, action="store", metavar="RIGHT",
                      help="second directory to compare")
    diff.add_argument("-t", "--timestamps", action="store_true",
                      help="show also files with equal checksum but different timestamps")
    diff.set_defaults(cmd=cmd_diff)

    backup = subparsers.add_parser("backup", aliases=["b"],
                                   help="make backup of a directory")
    backup.add_argument("source", type=Path, action="store", metavar="SRC",
                        help="source directory to backup")
    backup.add_argument("target", type=Path, action="store", metavar="DST",
                        help="target directory where backups are created")
    backup.add_argument("-f", "--full", action="store_true",
                        help="make a full backup")
    backup.set_defaults(cmd=cmd_backup)

    create = subparsers.add_parser("create", aliases=["c"],
                                   help="create the checksum files for directories")
    create.add_argument("dir", type=Path, action="store", nargs='+', metavar="DIR",
                        help="list of directories for which to compute checksums")
    create.set_defaults(cmd=cmd_create)

    verify = subparsers.add_parser("verify", aliases=["v"],
                                   help="verify the checksum files for directories")
    verify.add_argument("dir", type=Path, action="store", nargs='+', metavar="DIR",
                        help="list of directories for which to verify checksums")
    verify.set_defaults(cmd=cmd_verify)

    args = parser.parse_args()

    return args


def cmd_diff():
    report_diff(get_diff(ARGS.left, ARGS.right))


def cmd_backup():
    create_backup(ARGS.source, ARGS.target)


def cmd_create():
    process_directories(ARGS.dir, create_checksum)


def cmd_verify():
    process_directories(ARGS.dir, verify_checksum)


def create_backup(source, target):
    try:
        rel_path = source.resolve().relative_to(target.resolve())
        log("ABORTING : source must not be a sub-path of target", rel_path)
        return
    except:
        pass

    sub_target = target / source.name
    if not sub_target.exists():
        makedirs(sub_target)

    history = sorted(listdir(sub_target))
    if history:
        previous = sub_target / history[-1]
        log("using history", previous)
    else:
        previous = None
        log("no history found")

    while now_for_filename() == previous.name:
        sleep(1)
    current = sub_target / now_for_filename()
    log("create backup", current)
    makedirs(current)


def get_diff(dir1, dir2):
    if process_directories([dir1, dir2], create_checksum):
        diff = get_checksum_diff(load_checksums(dir1), load_checksums(dir2))
        for (path, change) in get_timestamp_diff(dircmp(dir1, dir2)).items():
            if ARGS.timestamps:
                if path in diff:
                    diff[path] = change + [diff[path]]
                else:
                    diff[path] = change
            elif path in diff:
                diff[path] = change
        return diff
    log("could not compare directories")
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
    for (current, _, files) in walk(path, onerror=lambda e: reraise(e)):
        for file in [Path(current) / f
                     for f in files]:
                    #  if not fnmatchcase(f, EXCLUDE_PATTERN)]:  # TODO
            file_subpath = str(file.relative_to(path))
            if not fnmatchcase(file_subpath, EXCLUDE_PATTERN):
                checksums[file_subpath] = METHODS[ARGS.method](file)
    return checksums


def reraise(exception):
    raise exception


def load_checksums(path):
    checksums = {}
    with open(path / SUM_FILE, "r", encoding="utf-8") as infile:
        for (checksum, file) in [line.rstrip().split(maxsplit=2, sep=" *./")
                                 for line in infile.readlines()]:
            checksums[str(Path(file))] = checksum
    return checksums


def get_timestamp_diff(comparison, prefix=Path(".")):
    result = {}
    for file in comparison.common_files:
        if not (prefix == Path(".") and fnmatchcase(file, EXCLUDE_PATTERN)):  # TODO
            time_a = stat(Path(comparison.left) / file).st_mtime
            time_b = stat(Path(comparison.right) / file).st_mtime
            if time_a != time_b:
                result[str(prefix / file)] = [TARGET_NEWER if time_a < time_b
                                              else TARGET_OLDER]
    for (sub_dir, sub_comparison) in comparison.subdirs.items():
        result.update(get_timestamp_diff(sub_comparison, prefix / sub_dir))
    return result


def report_diff(diff, parent=Path()):
    for path in sorted(diff.keys()):
        print("{:<2} {}".format("".join(diff[path]),
                                path_to_str(parent / path)))


def log(text, path=None):
    if not ARGS.quiet:
        if path:
            text = "%s : %s" % (text, path_to_str(path.resolve()))
        print("[{}] {}".format(now_for_log(), text), flush=True)


def path_to_str(path):
    return bytes(path).decode(stdout.encoding)


def now_for_log():
    return datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")


def now_for_filename():
    return datetime.now().strftime(r"%Y%m%d-%H%M%S")


def method_sha256(file):
    return calculate_digest(file, sha256())


def method_sha512(file):
    return calculate_digest(file, sha512())


def method_md5(file):
    return calculate_digest(file, md5())


def calculate_digest(file, digest):
    with open(file, "rb") as infile:
        buffer = infile.read()
        while buffer:
            digest.update(buffer)
            buffer = infile.read()
    return digest.hexdigest()


def method_size(file):
    return str(stat(file).st_size)


if __name__ == '__main__':
    ARGS = parse_args()

    SUM_FILE = 'chdiff.%s.txt' % ARGS.method
    EXCLUDE_PATTERN = 'chdiff.*.txt'

    BUFFER_SIZE = 16 * 1024 * 1024
    TARGET_MODIFIED = "*"
    TARGET_NEWER = "<"
    TARGET_OLDER = ">"
    TARGET_MISSING = "-"
    SOURCE_MISSING = "+"

    METHODS = {
        "sha256": method_sha256,
        "sha512": method_sha512,
        "md5": method_md5,
        "size": method_size,
    }

    ARGS.cmd()
