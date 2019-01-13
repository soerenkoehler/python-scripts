#!/usr/bin/env python3
# pylint: disable=C0103,C0111

# Solver for http://www.spiegel.de/wissenschaft/mensch/sechs-zahlen-auf-tuchfuehlung-raetsel-der-woche-a-1158691.html

from random import randint
from argparse import ArgumentParser


def index(a):
    return a[0]


def value(a):
    return a[1]


def is_all_equal(v):
    return min(v, key=value) == max(v, key=value)


def output_list(v):
    return list(map(value, sorted(v, key=index)))


def increment(a):
    return (index(a), value(a) + 1)


def increment_row(v, i, j):
    v[i] = increment(v[i])
    v[j] = increment(v[j])
    print(output_list(v))


def create_random_values(n):
    # index is kept for sorting output columns
    return [(i, randint(0, 9)) for i in range(n)]


def first_two_match(v):
    # expects a sorted list
    return value(v[0]) == value(v[1])


def exactly_first_three_match(v):
    # expects a sorted list
    # abort, if there are four or more minimal number
    if len(v) > 3 and value(v[0]) == value(v[3]):
        return False
    # check for three minimal numbers
    return value(v[0]) == value(v[2])


#
# startup preparations
#
PARSER = ArgumentParser()
PARSER.add_argument("-e", "--even", action="store_true",
                    help="ensure an even sum of the numbers")
PARSER.add_argument("n", type=int, help="count of numbers (min value = 3)")
args = PARSER.parse_args()

if args.n < 3:
    PARSER.exit("count of numbers must be >= 3")

#
# create initial vector
#
VECTOR = create_random_values(args.n)
while args.even and sum(map(value, VECTOR)) % 2 != 0:
    VECTOR = create_random_values(args.n)
print(output_list(VECTOR))

#
# do the game
#
while not is_all_equal(VECTOR):
    VECTOR.sort(key=value)
    # exactly three minimal numbers => 3-cycle
    if exactly_first_three_match(VECTOR):
        increment_row(VECTOR, 0, 1)
        increment_row(VECTOR, 0, 2)
        increment_row(VECTOR, 1, 2)
    # two minimal numbers => increase both
    elif first_two_match(VECTOR):
        increment_row(VECTOR, 0, 1)
    # one minimal number => increase it together with max number
    else:
        increment_row(VECTOR, 0, -1)
