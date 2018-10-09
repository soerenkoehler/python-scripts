#!/usr/bin/env python
# pylint: disable=C0111

import re
from urllib.request import urlopen
from urllib.parse import urljoin


def find(regexp, text):
    match = re.search(regexp, text, re.I)
    if match:
        return match.group(1)
    return None


def main():
    freefall = []

    print("--- scanning freefall history ---")

    last_url = "http://freefall.purrsia.com"
    # next_url = "grayff.htm"
    next_url = "/ff200/fv00102.htm"
    while next_url:
        last_url = urljoin(last_url, next_url)
        print(last_url)
        with urlopen(last_url) as response:
            html = str(response.read(), encoding='ISO-8859-1')
            image = find(r'<img src=".*?(\w+.gif)"', html)
            freefall.append((image,
                             find(r'<title>(.+)</title>', html),
                             urljoin(last_url, image)))
            next_url = find(r'<a href="(.+)">Previous</a>', html)

    print("--- downloading files ---")

    freefall_sorted = sorted(freefall, key=lambda x: x[0])
    for sublist in [freefall_sorted[i:i+10] for i in range(0, len(freefall_sorted), 10)]:
        print([entry[0] for entry in sublist])


main()
