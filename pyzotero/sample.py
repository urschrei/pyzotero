#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pyzotero.zotero as z

zot = z.Zotero('my_userID', 'my_userKey')
zot.add_parameters(limit = 1)
items = zot.top()
for item in items:
    print 'Title: %s\nItem ID: %s\n' % (
    item['title'], item['id'])
