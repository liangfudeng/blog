#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Blog handler for urls
version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
"""

import os

import config
from __init__ import entryService

render = config.render
web = config.web
config = config.blogconfig

SITE_PATH = 'c:\\liangfudeng.github.io'


def save_html(content, path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    open(path, 'w').write(content)


def build_index():
    limit = 10
    start = 0
    params = entryService.search(entryService.types.index, config.index_url, '', start, limit)
    save_html(str(render.index(params)), os.path.join(SITE_PATH, 'index.html'))


def build_archive():
    url = config.archive_url
    params = entryService.archive(entryService.types.entry, url)
    if params.entries is None:
        raise web.notfound(render.error(params))
    save_html(str(render.archive(params)), os.path.join(SITE_PATH, 'archive.html'))


def build_category():
    all_categorys = entryService.get_all_catagories()
    save_html(str(render.category(all_categorys)), os.path.join(SITE_PATH, 'category.html'))


def build_entry():
    for it in entryService.urls:
        params = entryService.find_by_url(entryService.types.entry, it)
        save_html(str(render.entry(params)), os.path.join(SITE_PATH, "." + it))


if __name__ == '__main__':
    build_index()
    build_category()
    build_archive()
    build_entry()
    build_category()
