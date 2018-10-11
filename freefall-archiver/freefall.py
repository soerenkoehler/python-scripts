#!/usr/bin/env python
# pylint: disable=C0111

import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

IMG_PER_PAGE = 10

HTML_INDEX_ENTRY = """<a href="ff%05d/index.html">%s - %s</a>"""
HTML_PAGE_ENTRY = """%s<br/>
<img src="%s"/>"""
HTML_MAIN = u"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<title>%s</title>
</head><body>
<p>%s</p>
<hr>
<a href="http://freefall.purrsia.com/grayff.htm">&copy; http://freefall.purrsia.com/grayff.htm"</a>
</body>
</html>"""


def main():
    freefall = []

    print("--- scanning freefall history ---")

    last_url = "http://freefall.purrsia.com"
    # next_url = "grayff.htm"
    next_url = "/ff100/fv00012.htm"
    while next_url:
        last_url = urljoin(last_url, next_url)
        print(last_url)
        with urlopen(last_url) as response:
            html = str(response.read(), encoding='ISO-8859-1')
            image, title_old, title_new, next_url = parse_freefall_page(html)
            freefall.append((image,
                             title_old if title_old else title_new,
                             urljoin(last_url, image)))

    print("--- downloading files ---")

    index = []
    freefall_sorted = [entry for entry in reversed(freefall)]

    for sublist in [(i / IMG_PER_PAGE, freefall_sorted[i:i+10])
                    for i in range(0, len(freefall_sorted), 10)]:
        index.append(HTML_INDEX_ENTRY %
                     (sublist[0], sublist[1][0][1], sublist[1][-1][1]))
        subdir = Path("ff%05d" % sublist[0])
        subdir.mkdir(parents=True, exist_ok=True)
        with open(subdir / "index.html", "w") as out_page:
            out_page.write(HTML_MAIN)

    with open("index.html", "w") as out_index:
        out_index.write(HTML_MAIN % ("Freefall Index", "</p><p>".join(index)))


def parse_freefall_page(html):
    return (
        find(r'<img src=".*?(\w+.gif)"', html),
        find(r'<!-+\s(.+)\s-+>', html),
        find(r'<title>(.+)</title>', html),
        find(r'<a href="(.+)">Previous</a>', html)
    )


def find(regexp, text):
    match = re.search(regexp, text, re.I)
    if match:
        return match.group(1)
    return None


main()
