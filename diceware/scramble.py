#!/usr/bin/env python

from argparse import ArgumentParser
from random import seed, randrange

parser = ArgumentParser("Diceware String Encode")
parser.add_argument('-d', action='store_const', dest='isDecode', const=True)
parser.add_argument('input')
args = parser.parse_args()

seed()

def scramble(x):
	if args.isDecode:
		return (ord(x) - ord('a')) % 6 + ord('1')
	else:
		return ord(x) - ord('1') + ord('a') + randrange(0, 24, 6)

print("".join([chr(scramble(x)) for x in args.input]))
