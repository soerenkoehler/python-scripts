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
    last_url = "http://freefall.purrsia.com"
    next_url = "/ff100/fv00002.htm" # "grayff.htm"
    while next_url:
        last_url = urljoin(last_url, next_url)
        print(last_url)
        with urlopen(last_url) as response:
            html = str(response.read(), encoding='ISO-8859-1')
            freefall.append((find(r'<a href="(.+)">.*<img src="\1"', html),
                             find(r'<title>(.+)</title>', html)))
            next_url = find(r'<a href="(.+)">Previous</a>', html)


PATH = 2  # index in parse result

main()
