#!/usr/bin/env python3

with open("eff_short_wordlist_1.txt", "r") as infile:
    with open("reformatted.txt", "w") as output:
        output.write(
            "\n".join([
                "\t".join([
                    infile.readline().strip()
                    for i in range(6)])
                for j in range(216)]))
