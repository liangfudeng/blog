#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Entry Service.

version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
2013-11-23    dylanninin@gmail.com     update tags, categories

"""
import traceback

import os
import codecs
import re
import datetime
import random

import markdown

from config import blogconfig as config
from tool import Extract
from model import Models

extract = Extract()


class EntryService(object):
    """EntryService."""

    def __init__(self):
        self.entries = {}
        self.pages = {}
        self.urls = []
        self.by_tags = {}
        self.by_categories = {}
        self.by_months = {}
        self.models = Models()
        self.types = self.models.types()
        self.params = self.models.params()
        self._init_blog()

    def _init_blog(self):
        """
        Initialize blog
            - all entries in entry_dir
            - all pages in page_dir
            - others
        """
        for root, _, files in os.walk(config.entry_dir):
            for f in files:
                self.add_entry(False, root + '/' + f)
        for root, _, files in os.walk(config.page_dir):
            for f in files:
                self._add_page(root + '/' + f)
        self._init_miscellaneous(self.types.add, self.entries.values())

    def add_entry(self, inotified, path):
        """
        Add entry
        """
        entry = self._init_entry(self.types.entry, path)
        if entry is not None:
            self.entries[entry.url] = entry
            if inotified:
                self._init_miscellaneous(self.types.add, [entry])

    def delete_entry(self, path):
        """
        Delete entry
        """
        for entry in self.entries.values():
            if path == os.path.abspath(entry.path):
                self.entries.pop(entry.url)
                self._init_miscellaneous(self.types.delete, [entry])

    def _add_page(self, path):
        """
        Add page
        """
        page = self._init_entry(self.types.page, path)
        if page is not None:
            self.pages[page.url] = page

    def _init_entry(self, entry_type, path):
        """
        initialize single entry
        """
        url, raw_url, name, date, time, content = self._init_file(path, entry_type)
        if url is not None:
            entry = self.models.entry(entry_type)
            entry.path = path
            entry.name = name
            entry.url = url
            entry.raw_url = raw_url
            entry.date = date
            entry.time = time
            header, title, categories, tags = extract.parse(entry)
            entry.content = content
            content = content.replace(header, '')
            entry.html = markdown.markdown(content)
            # FIXME How to extract the excerpt of an entry
            entry.excerpt = content[:200] + ' ... ...'
            entry.categories = categories
            entry.tags = tags
            return entry
        return None

    def _init_file(self, file_path, entry_type):
        """
        Initialize single file
        """
        # FIXME: how to determine the publish time of an entry
        content, nones = None, [None for _ in xrange(6)]
        try:
            content = codecs.open(file_path, mode='r', encoding='utf-8').read()
        except:
            return nones
        if content is None or len(content.strip()) == 0:
            return nones
        date, mtime = None, None
        name, _ = os.path.splitext(os.path.basename(file_path))
        chars = ['_', '-', '~']
        pattern = r'\d{4}-\d{1,2}-\d{1,2}'
        match = re.search(pattern, name)
        if match:
            y, m, d = match.group().split('-')
            try:
                date = datetime.date(int(y), int(m), int(d))
            except:
                print traceback.format_exc()
                print file_path
            name = name[len(match.group()):]
            for c in chars:
                if name.startswith(c):
                    name = name[1:]
        stat = os.stat(file_path)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        if date is None:
            date = mtime
        prefix, url_prefix, raw_prefix = date.strftime(config.url_date_fmt), '', ''
        if entry_type == self.types.entry:
            url_prefix = config.entry_url + '/' + prefix + '/'
            raw_prefix = config.raw_url + '/' + prefix + '/'
        elif entry_type == self.types.page:
            url_prefix = '/'
            raw_prefix = config.raw_url + '/'
        date = date.strftime(config.date_fmt)
        time = date + mtime.strftime(config.time_fmt)[len('yyyy-mm-dd'):]
        url = url_prefix + name + config.url_suffix
        raw_url = raw_prefix + name + config.raw_suffix
        for c in chars:
            name = name.replace(c, ' ')
        return url, raw_url, name, date, time, content

    def _init_miscellaneous(self, init_type, entries):
        """
        Initialize miscellaneous
            - tags
            - categories
            - archives
            - all urls
        """
        for entry in entries:
            self._init_tag(init_type, entry.url, entry.tags)
            self._init_category(init_type, entry.url, entry.categories, entry)
            self._init_monthly_archive(init_type, entry.url)
        self.urls = sorted(self.entries.keys(), reverse=True)
        self._init_params()

    def _init_subscribe(self):
        """
        Initialize subscriptions
        """
        if not self.urls:
            time = datetime.datetime.now().strftime(config.time_fmt)
        else:
            time = self.entries[self.urls[0]].time
        return self.models.subscribe(time)

    def _init_tag(self, init_type, url, tags):
        """
        Initialize tags
        """
        for tag in tags:
            if tag not in self.by_tags:
                if init_type == self.types.add:
                    self.by_tags[tag] = self.models.tag(tag, url)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_tags[tag].urls.insert(0, url)
                    self.by_tags[tag].count += 1
                if init_type == self.types.delete:
                    self.by_tags[tag].count -= 1
                    self.by_tags[tag].urls.remove(url)
                    if self.by_tags[tag].count == 0:
                        self.by_tags.pop(tag)

    def _init_category(self, init_type, url, categories, entry):
        """
        Initialize categories
        """
        for category in categories:
            if category not in self.by_categories:
                if init_type == self.types.add:
                    self.by_categories[category] = \
                        self.models.category(category, url, entry.name)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_categories[category].urls.insert(0, (url, entry.name))
                    self.by_categories[category].count += 1
                if init_type == self.types.delete:
                    self.by_categories[category].count -= 1
                    self.by_categories[category].urls.remove((url, entry.name))
                    if self.by_categories[category].count == 0:
                        self.by_categories.pop(category)

    def _init_monthly_archive(self, init_type, url):
        """
        Initialize archives
        """
        start = len(config.entry_url) + 1
        end = start + len('/yyyy/mm')
        month = url[start:end]
        if month not in self.by_months:
            if init_type == self.types.add:
                self.by_months[month] = \
                    self.models.monthly_archive(self.types.entry, month, url)
            if init_type == self.types.delete:
                pass
        else:
            if init_type == self.types.add:
                self.by_months[month].urls.insert(0, url)
                self.by_months[month].count += 1
            else:
                self.by_months[month].count -= 1
                self.by_months[month].urls.remove(url)
                if self.by_months[month].count == 0:
                    self.by_months.pop(month)

    def _init_params(self):
        """
        Initialize global params
        :return:
        """
        self.params.subscribe = self._init_subscribe()
        self.params.primary.tags = self._init_tags_widget()
        self.params.primary.recently_entries = self._init_recently_entries_widget()
        self.params.secondary.categories = self._init_categories_widget()
        self.params.secondary.calendar = self._init_calendar_widget()
        self.params.secondary.archive = self._init_archive_widget()

    def _init_related_entries(self, url):
        """
        Initialize related entries
        """
        # FIXME: related entries
        try:
            index = self.urls.index(url)
        except:
            print traceback.format_exc()
            return None
        urls = self.urls[:index]
        urls.extend(self.urls[index + 1:])
        urls = random.sample(urls, min(len(urls), 10))
        return [self.entries.get(url) for url in sorted(urls, reverse=True)]

    def _init_abouts_widget(self, about_types=None, url=None):
        """
        Initialize abouts widget
        :param about_types:
        :param url:
        :return:
        """
        about_types = about_types or []
        abouts = []
        for about_type in about_types:
            about = self.models.about(about_type)
            if about_type == self.types.entry and url is not None:
                try:
                    i = self.urls.index(url)
                    p, n = i + 1, i - 1
                except:
                    print traceback.format_exc()
                    p, n = 999999999, -1
                if p < len(self.urls):
                    url = self.urls[p]
                    about.prev_url = url
                    about.prev_name = self.entries[url].name
                if n >= 0:
                    url = self.urls[n]
                    about.next_url = url
                    about.next_name = self.entries[url].name
            if about_type == self.types.archive:
                about.prev_url = '/'
                about.prev_name = 'main index'
            elif about_type == self.types.blog:
                about.prev_url = '/'
                about.prev_name = 'main  index'
                about.next_url = config.archive_url
                about.next_name = 'archives'
            abouts.append(about)
        return abouts

    def _init_tags_widget(self):
        """
        Initialize tags widget
        """
        # FIXME: calculate tags' rank
        tags = sorted(self.by_tags.values(), key=lambda v: v.count, reverse=True)
        ranks = config.ranks
        div, mod = divmod(len(tags), ranks)
        if div == 0:
            ranks, div = mod, 1
        for r in range(ranks):
            s, e = r * div, (r + 1) * div
            for tag in tags[s:e]:
                tag.rank = r + 1
        return tags

    def _init_recently_entries_widget(self):
        """
        Initialize recently entries widget
        :return:
        """
        return [self.entries[url] for url in self.urls[:config.recently]]

    def _init_calendar_widget(self):
        """
        Initialize calender widget
        :return:
        """
        date = datetime.datetime.today().strftime(config.date_fmt)
        if len(self.urls) > 0:
            date = self.entries[self.urls[0]].date
        calendar = self.models.calendar(date)
        y, m = calendar.month.split('-')
        for url in self.urls:
            _, _, _, _, d, _ = url.split('/')
            prefix = config.entry_url + '/' + y + '/' + m + '/' + d
            d = int(d)
            if url.startswith(prefix):
                calendar.counts[d] += 1
                if calendar.counts[d] > 1:
                    start = len(config.entry_url)
                    end = start + len('/yyyy/mm/dd')
                    calendar.urls[d] = config.archive_url + url[start:end]
                else:
                    calendar.urls[d] = url
            else:
                break
        return calendar

    def _init_categories_widget(self):
        """
        Initialize categories widget
        :return:
        """
        return sorted(self.by_categories.values(), key=lambda c: c.name)

    def _init_archive_widget(self):
        """
        Initialize archive widget
        :return:
        """
        return sorted(self.by_months.values(), key=lambda m: m.url, reverse=True)

    def _find_by_query(self, query, start, limit):
        """
        Find by query
        :param query:
        :param start:
        :param limit:
        :return:
        """
        # FIXME: how to search in the content of entries
        queries = [q.lower() for q in query.split(' ')]
        urls = []
        for query in queries:
            for entry in self.entries.values():
                try:
                    entry.content.index(query)
                    urls.append(entry.url)
                except:
                    print
        return self._find_by_page(sorted(urls), start, limit)

    def _find_by_page(self, urls, start, limit):
        """
        Find by page
        :param urls:
        :param start:
        :param limit:
        :return:
        """
        if urls is None or start < 0 or limit <= 0:
            return [], 0
        total = len(urls)
        urls = sorted(urls, reverse=True)
        s, e = (start - 1) * limit, start * limit
        if s > total or s < 0:
            return [], 0
        return [self.entries[url] for url in urls[s:e]], total

    def _paginate(self, pager_type, value, total, start, limit):
        """
        Pagination
        :param pager_type:
        :param value:
        :param total:
        :param start:
        :param limit:
        :return:
        """
        if limit <= 0:
            return self.models.pager(pager_type, value, total, 0, start, limit)
        pages, mod = divmod(total, limit)
        if mod > 0:
            pages += 1
        return self.models.pager(pager_type, value, total, pages, start, limit)

    def find_by_url(self, entry_type, url):
        """
        Find content by url
        :param entry_type:
        :param url:
        :return:
        """
        entry, abouts = None, [self.types.blog]
        if entry_type == self.types.entry:
            entry = self.entries.get(url)
            abouts.insert(0, self.types.entry)
        elif entry_type == self.types.page:
            entry = self.pages.get(url)
        self.params.entry = entry
        self.params.entries = self._init_related_entries(url)
        self.params.error = self.models.error(url=url)
        self.params.primary.abouts = self._init_abouts_widget(abouts, url)
        return self.params

    def find_raw(self, raw_url):
        """
        Find the raw content by raw_url
        :param raw_url:
        :return:
        """
        page_url = raw_url.replace(config.raw_url, '').replace(config.raw_suffix, config.url_suffix)
        page = self.find_by_url(self.types.page, page_url).entry
        if page is not None and page.raw_url == raw_url:
            return page.content

        entry_url = raw_url.replace(config.raw_url, config.entry_url).replace(config.raw_suffix, config.url_suffix)
        entry = self.find_by_url(self.types.entry, entry_url).entry
        if entry is not None and entry.raw_url == raw_url:
            return entry.content
        return None

    def archive(self, archive_type, url, start=1, limit=999999999):
        """
        Archives
        :param archive_type:
        :param url:
        :param start:
        :param limit:
        :return:
        """
        self.params.error = self.models.error(url=url)

        if archive_type == self.types.raw:
            url = url.replace(config.raw_url, config.archive_url)

        entries, count, = [], 0
        archive_url = url.replace(config.archive_url, '').strip('/')
        prefix = url.replace(config.archive_url, config.entry_url)
        pattern = r'\d{4}/\d{2}/\d{2}|\d{4}/\d{2}|\d{4}'
        match = re.search(pattern, archive_url)
        if match and match.group() == archive_url or archive_url == '':
            urls = [url for url in self.urls if url.startswith(prefix)]
            entries, _ = self._find_by_page(urls, start, limit)
            count = len(entries)
        else:
            entries = None
        if archive_url == '':
            archive_url = self.types.all

        self.params.entries = entries
        self.params.archive = self.models.archive(archive_type, url, archive_url, url, count)
        self.params.primary.abouts = self._init_abouts_widget([self.types.archive])
        return self.params

    def search(self, search_type, url, value='', start=config.start, limit=config.limit):
        """
        Search the site
        :param search_type:
        :param url:
        :param value:
        :param start:
        :param limit:
        :return:
        """
        entries, total, abouts = None, 0, [self.types.blog]
        if search_type == self.types.query:
            entries, total = self._find_by_query(value, start, limit)
        elif search_type == self.types.tag:
            if self.by_tags.get(value) is None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_tags.get(value).urls, start, limit)
        elif search_type == self.types.category:
            if self.by_categories.get(value) is None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_categories.get(value).urls, start, limit)
        elif search_type == self.types.index:
            entries, total = self._find_by_page(self.urls, start, limit)
            abouts = []
        self.params.error = self.models.error(url=url)
        self.params.entries = entries
        self.params.search = self.models.search(search_type, value, total)
        self.params.pager = self._paginate(search_type, value, total, start, limit)
        self.params.primary.abouts = self._init_abouts_widget(abouts)
        return self.params

    def get_all_catagories(self):
        return self.by_categories

    def error(self, url):
        """
        Error params
        :param url:
        :return:
        """
        self.params.error = self.models.error(url=url)
        self.params.primary.abouts = self._init_abouts_widget([self.types.blog])
        return self.params


if __name__ == '__main__':
    import doctest

    doctest.testmod()
