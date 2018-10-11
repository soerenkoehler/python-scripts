#!/usr/bin/env python
# pylint: disable=C0111

import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

IMG_PER_PAGE = 10

CSS_VISIBLE = "visible"
CSS_HIDDEN = "hidden"
HTML_INDEX_ENTRY = """<a href="ff%05d/index.html">%s - %s</a>"""
HTML_PAGE_ENTRY = """%s<br/>
<img src="%s"/>"""
HTML_PAGE_NAV = """<a href="../ff%05d/index.html" style="visibility: %s">Previous</a>
<span style="visibility: %s">&nbsp;-&nbsp;</span>
<a style="visibility: %s" href="../ff%05d/index.html">Next</a>"""
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
    with open("index.html", "w") as out_index:
        out_index.write(HTML_MAIN % ("Freefall Index",
                                     "</p><p>".join(write_pages(scan_freefall()))))


def write_pages(freefall):
    result = []

    partitions = partition(freefall, IMG_PER_PAGE)
    for page in partitions:
        image_list = page[1]
        von, bis = image_list[0][1], image_list[-1][1]
        result.append(HTML_INDEX_ENTRY % (page[0], von, bis))
        subdir = Path("ff%05d" % page[0])
        subdir.mkdir(parents=True, exist_ok=True)
        for image in image_list:
            with urlopen(image[2]) as response:
                with open(subdir / image[0], "wb") as out_image:
                    out_image.write(response.read())
                    print(image[2])
        with open(subdir / "index.html", "w") as out_page:
            out_page.write(HTML_MAIN % (
                "%s - %s" % (von, bis),
                "</p><p>".join(create_nav(page, len(partitions)))))
    return result


def create_nav(page, max_nav):
    prev_page = page[0]-1
    next_page = page[0]+1
    prev_visible = prev_page >= 0
    next_visible = next_page < max_nav
    nav = HTML_PAGE_NAV % (prev_page,
                           css_visibility(prev_visible),
                           css_visibility(prev_visible and next_visible),
                           css_visibility(next_visible),
                           next_page)
    return [nav] + [HTML_PAGE_ENTRY % (entry[1], entry[0]) for entry in page[1]] + [nav]


def css_visibility(visible):
    return CSS_VISIBLE if visible else CSS_HIDDEN


def scan_freefall():
    result = []
    last_url = "http://freefall.purrsia.com"
    next_url = "grayff.htm"
    while next_url:
        last_url = urljoin(last_url, next_url)
        print(last_url)
        with urlopen(last_url) as response:
            html = str(response.read(), encoding='ISO-8859-1')
            image, title_old, title_new, next_url = parse_freefall_page(html)
            result.append((image,
                           title_old if title_old else title_new,
                           urljoin(last_url, image)))
    return [e for e in reversed(result)]


def partition(data, step):
    return [(i / step, data[i:i+step]) for i in range(0, len(data), step)]


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
