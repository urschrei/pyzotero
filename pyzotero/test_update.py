#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyzotero import zotero
zot = zotero.Zotero(436, 'qmf7yjuu8uegfsa3p4p7zllk')
zot.add_parameters(limit=1)
i = zot.items()
i[0]['title'] = u"Hell, I don't know"
zot.update_item(i[0])


