"""BibTeX that Zotero exports, and the parser for it."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import bibtexparser


def parse_bibtex(text: str) -> list[dict[str, str]]:
    """Parse BibTeX source into a list of entries, with month macros expanded.

    Each entry is a dict of its fields, with the citation key in ``ID`` and the
    entry type in ``ENTRYTYPE``.
    """
    parser = bibtexparser.bparser.BibTexParser(
        common_strings=True, ignore_nonstandard_types=False
    )
    return parser.parse(text).entries


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
