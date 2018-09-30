#!/usr/bin/env python

from argparse import ArgumentParser
from random import seed, randrange


def scramble(x):
    if args.isDecode:
        return (ord(x) - ord('a')) % 6 + ord('1')
    return ord(x) - ord('1') + ord('a') + randrange(0, 24, 6)


def group(x):
    group_size = int(args.groupSize)
    if args.isDecode and len(x) > group_size:
        return x[0:group_size] + " " + group(x[group_size:])
    return x


parser = ArgumentParser("Diceware String Encode")
parser.add_argument('-d', action='store_const', dest='isDecode', const=True)
parser.add_argument('-g', '--group-size', action='store', dest='groupSize', default=4)
parser.add_argument('input')
args = parser.parse_args()

seed()

print(group("".join([chr(scramble(x)) for x in args.input.replace(' ', '')])))
