#!/usr/bin/env python3
# pylint: disable=C0111

from argparse import ArgumentParser
from datetime import datetime
from filecmp import dircmp
from fnmatch import fnmatchcase
from hashlib import md5, sha256, sha512
from os import listdir, makedirs, stat, walk
from pathlib import Path
from sys import stdout
from time import sleep
from shutil import copy2, move


def parse_args():
    parser = ArgumentParser(
        description="ChDiff - a checksum based diff and backup tool")

    parser.set_defaults(cmd=parser.print_help)

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
                                   help="create the checksum files for a list of directories")
    create.add_argument("dir", type=Path, action="store", nargs='+', metavar="DIR",
                        help="a directorie-path to compute checksums for")
    create.set_defaults(cmd=cmd_create)

    verify = subparsers.add_parser("verify", aliases=["v"],
                                   help="verify the checksum files for a list of directories")
    verify.add_argument("dir", type=Path, action="store", nargs='+', metavar="DIR",
                        help="a directorie-path to verify checksums for")
    verify.set_defaults(cmd=cmd_verify)

    for sub_parser in [diff, backup, create, verify]:
        sub_parser.set_defaults(quiet=0)
        sub_parser.add_argument("-q", "--quiet", dest="quiet",
                                action="store_const", const=1,
                                help="dont print progress info")
        sub_parser.add_argument("-qq", "--very-quiet", dest="quiet",
                                action="store_const", const=2,
                                help="dont print warnings")
        sub_parser.add_argument("-m", "--method", action="store", default="sha256",
                                choices=["sha256", "sha512", "md5", "size"],
                                help="the checksum method to use")

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
        log("ABORTING : source must not be a sub-path of target", rel_path, level=3)
        return
    except:  # pylint: disable=w0702
        pass

    sub_target = target / source.name
    if not sub_target.exists():
        makedirs(sub_target)

    previous, previous_checksums = load_previous(sub_target)

    current = sub_target / \
        now_for_filename(previous.name if previous else None)
    log("create backup", current)
    makedirs(current)

    process_directories([source], create_checksum)

    diff = get_checksum_diff(calculate_checksums(source),
                             previous_checksums, True)
    cnt_new, cnt_same, cnt_delete = 0, 0, 0
    for (file, change) in diff.items():
        dst = current / file
        if change == BOTH_EQUAL:
            if not dst.parent.exists():
                makedirs(dst.parent)
            move(previous / file, dst)
            cnt_same += 1
        elif change == TARGET_MISSING:
            if not dst.parent.exists():
                makedirs(dst.parent)
            copy2(source / file, dst)
            cnt_new += 1
        else:
            cnt_delete += 1
    copy2(source / resolve_sum_file(), current / resolve_sum_file())
    log("    new files: %s" % cnt_new, level=2)
    log("   same files: %s" % cnt_same, level=2)
    log("deleted files: %s" % cnt_delete, level=2)


def load_previous(sub_target):
    history = sorted(listdir(sub_target))
    if history:
        previous = sub_target / history[-1]
        log("using history", previous)

        try:
            return previous, load_checksums(previous)
        except FileNotFoundError as file_not_found:
            log("file not found", Path(file_not_found.filename), level=2)
    else:
        log("no history found", level=2)

    log("making full backup")
    return None, {}


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
    log("could not compare directories", level=2)
    return {}


def process_directories(directories, function):
    result = True
    for path in [Path(d) for d in directories]:
        try:
            log("scanning", path)
            log(function(path), path / resolve_sum_file(), level=2)
        except FileNotFoundError as file_not_found:
            log("file not found", Path(file_not_found.filename), level=2)
            result = False
    return result


def create_checksum(path):
    checksums = calculate_checksums(path)
    with open(path / resolve_sum_file(), "w", encoding="utf-8") as out:
        out.write("\n".join(
            ["%s *./%s" % (checksums[f], f) for f in sorted(checksums)]))
    return "created"


def verify_checksum(path):
    diff = get_checksum_diff(load_checksums(path), calculate_checksums(path))
    report_diff(diff, path.resolve())
    return "%s difference(s) found" % len(diff) if diff else "OK"


def get_checksum_diff(source, target, report_equals=False):
    diff = {}
    for file in [f for f in source if f in target]:
        if target[file] == source[file]:
            if report_equals:
                diff[file] = BOTH_EQUAL
        else:
            diff[file] = TARGET_MODIFIED
    for file in [f for f in source if f not in target]:
        diff[file] = TARGET_MISSING
    for file in [f for f in target if f not in source]:
        diff[file] = SOURCE_MISSING
    return diff


def calculate_checksums(path):
    checksums = {}
    for (current, _, files) in walk(path, onerror=print):
        for file in [Path(current) / f
                     for f in files]:
            file_subpath = str(file.relative_to(path).as_posix())
            if not fnmatchcase(file_subpath, EXCLUDE_PATTERN):
                try:
                    checksums[file_subpath] = METHODS[ARGS.method](file)
                except (PermissionError, IOError) as error:
                    print(error)
    return checksums


def load_checksums(path):
    checksums = {}
    with open(path / resolve_sum_file(), "r", encoding="utf-8") as infile:
        for (checksum, file) in [line.rstrip().split(maxsplit=2, sep=" *./")
                                 for line in infile.readlines()]:
            checksums[str(Path(file).as_posix())] = checksum
    return checksums


def get_timestamp_diff(comparison, prefix=Path(".")):
    result = {}
    for file in comparison.common_files:
        if not (prefix == Path(".") and fnmatchcase(file, EXCLUDE_PATTERN)):
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


def log(text, path=None, level=1):
    if level > ARGS.quiet:
        if path:
            text = "{} : {}".format(text, path_to_str(path.resolve()))
        print("[{}] {}".format(now_for_log(), text), flush=True)


def path_to_str(path):
    return bytes(path).decode(stdout.encoding)


def now_for_filename(avoid_this_name):
    result = now_formatted(r"%Y%m%d-%H%M%S")
    while result == avoid_this_name:
        sleep(1)
    return result


def now_for_log():
    return now_formatted(r"%Y-%m-%d %H:%M:%S")


def now_formatted(pattern):
    return datetime.now().strftime(pattern)


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


def resolve_sum_file():
    return SUM_FILE % ARGS.method


SUM_FILE = 'chdiff.%s.txt'
EXCLUDE_PATTERN = 'chdiff.*.txt'

BUFFER_SIZE = 16 * 1024 * 1024

BOTH_EQUAL = "="
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


if __name__ == '__main__':
    ARGS = parse_args()
    ARGS.cmd()
