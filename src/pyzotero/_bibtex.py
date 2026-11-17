"""BibTeX that Zotero exports, and the parser for it."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import bibtexparser
from bibtexparser.middlewares import (
    MonthLongStringMiddleware,
    NormalizeFieldKeys,
    default_parse_stack,
)
from bibtexparser.model import DuplicateBlockKeyBlock, Entry


def parse_bibtex(text: str) -> list[dict[str, str]]:
    """Parse BibTeX source into a list of entries, with month names expanded.

    Each entry is a dict of its fields, with the citation key in ``ID`` and the
    entry type in ``ENTRYTYPE``. Field names are in lower case. A month macro
    or number becomes the full month name. An entry with the same key as an
    earlier entry is kept.
    """
    library = bibtexparser.parse_string(
        text,
        parse_stack=[
            *default_parse_stack(),
            NormalizeFieldKeys(),
            MonthLongStringMiddleware(),
        ],
    )
    strings = "".join(f"{string.raw}\n" for string in library.strings)
    entries: list[dict[str, str]] = []
    for block in library.blocks:
        if isinstance(block, Entry):
            entries.append(dict(block))
        elif (
            isinstance(block, DuplicateBlockKeyBlock)
            and isinstance(block.ignore_error_block, Entry)
            and block.ignore_error_block.raw
        ):
            # bibtexparser does not apply the parse stack to a duplicate.
            # Parse the duplicate again, with the string definitions.
            entries.extend(parse_bibtex(strings + block.ignore_error_block.raw))
    return entries


@dataclass(frozen=True)
class BibTeX:
    """BibTeX that Zotero exports for a ``format="bibtex"`` request.

    ``text`` is the BibTeX source as Zotero sends it. Write it to a file to
    get a ``.bib`` file. ``entries`` is the parsed entries: a list of dicts
    with the citation key in ``ID``, the entry type in ``ENTRYTYPE``, and one
    key for each field. Field values are not decoded from LaTeX.
    """

    text: str

    @cached_property
    def entries(self) -> list[dict[str, str]]:
        """The parsed entries, in source order."""
        return parse_bibtex(self.text)

    @classmethod
    def join(cls, parts: list[BibTeX]) -> BibTeX:
        """Join the BibTeX from several responses, for example from pages."""
        return cls("\n\n".join(p.text.strip() for p in parts if p.text.strip()))

    def __str__(self) -> str:
        return self.text
