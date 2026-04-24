"""Saved search functionality for Pyzotero.

This module contains the SavedSearch class for creating and managing
Zotero saved searches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import errors as ze

if TYPE_CHECKING:
    from ._client import Zotero


class SavedSearch:
    """Saved search functionality.

    See https://github.com/zotero/zotero/blob/master/chrome/content/zotero/xpcom/data/searchConditions.js
    """

    def __init__(self, zinstance: Zotero) -> None:
        super().__init__()
        self.zinstance: Zotero = zinstance
        self.searchkeys: tuple[str, str, str] = ("condition", "operator", "value")
        # always exclude these fields from zotero.item_keys()
        self.excluded_items: tuple[str, ...] = (
            "accessDate",
            "date",
            "pages",
            "section",
            "seriesNumber",
            "issue",
        )
        self.operators = {
            "is": "is",
            "isNot": "isNot",
            "beginsWith": "beginsWith",
            "contains": "contains",
            "doesNotContain": "doesNotContain",
            "isLessThan": "isLessThan",
            "isGreaterThan": "isGreaterThan",
            "isBefore": "isBefore",
            "isAfter": "isAfter",
            "isInTheLast": "isInTheLast",
            "any": "any",
            "all": "all",
            "true": "true",
            "false": "false",
        }
        # common groupings of operators
        self.groups = {
            "A": ("true", "false"),
            "B": ("any", "all"),
            "C": ("is", "isNot", "contains", "doesNotContain"),
            "D": ("is", "isNot"),
            "E": ("is", "isNot", "isBefore", "isInTheLast"),
            "F": ("contains", "doesNotContain"),
            "G": (
                "is",
                "isNot",
                "contains",
                "doesNotContain",
                "isLessThan",
                "isGreaterThan",
            ),
            "H": ("is", "isNot", "beginsWith"),
            "I": ("is",),
        }
        self.conditions_operators = {
            "deleted": self.groups["A"],
            "noChildren": self.groups["A"],
            "unfiled": self.groups["A"],
            "publications": self.groups["A"],
            "retracted": self.groups["A"],
            "includeParentsAndChildren": self.groups["A"],
            "includeParents": self.groups["A"],
            "includeChildren": self.groups["A"],
            "recursive": self.groups["A"],
            "joinMode": self.groups["B"],
            "quicksearch-titleCreatorYear": self.groups["C"],
            "quicksearch-titleCreatorYearNote": self.groups["C"],
            "quicksearch-fields": self.groups["C"],
            "quicksearch-everything": self.groups["C"],
            "collectionID": self.groups["D"],
            "savedSearchID": self.groups["D"],
            "collection": self.groups["D"],
            "savedSearch": self.groups["D"],
            "dateAdded": self.groups["E"],
            "dateModified": self.groups["E"],
            "itemType": self.groups["D"],
            "fileTypeID": self.groups["D"],
            "tagID": self.groups["D"],
            "tag": self.groups["C"],
            "note": self.groups["F"],
            "childNote": self.groups["F"],
            "creator": self.groups["C"],
            "lastName": self.groups["C"],
            "field": self.groups["C"],
            "datefield": self.groups["E"],
            "year": self.groups["C"],
            "numberfield": self.groups["G"],
            "libraryID": self.groups["D"],
            "key": self.groups["H"],
            "itemID": self.groups["D"],
            "annotationText": self.groups["F"],
            "annotationComment": self.groups["F"],
            "fulltextWord": self.groups["F"],
            "fulltextContent": self.groups["F"],
            "tempTable": self.groups["I"],
        }
        # Aliases
        for pf in (
            "pages",
            "numPages",
            "numberOfVolumes",
            "section",
            "seriesNumber",
            "issue",
        ):
            self.conditions_operators[pf] = self.groups["G"]
        for df in ("accessDate", "date", "dateDue", "accepted"):
            self.conditions_operators[df] = self.groups["E"]
        # aliases for field - this makes a blocking API call unless item types have been cached
        excluded = set(self.excluded_items)
        for itm in self.zinstance.item_fields():
            field = itm["field"]  # ty: ignore[invalid-argument-type]
            if field not in excluded:
                self.conditions_operators[field] = self.groups["C"]

    def _validate(self, conditions: list[dict[str, str]]) -> None:
        """Validate saved search conditions.

        Raises an error if any contain invalid operators.
        """
        allowed_keys = set(self.searchkeys)
        for condition in conditions:
            if set(condition.keys()) != allowed_keys:
                msg = f"Keys must be all of: {', '.join(self.searchkeys)}"
                raise ze.ParamNotPassedError(msg)
            operator = condition.get("operator")
            if operator not in self.operators:
                msg = f"You have specified an unknown operator: {operator}"
                raise ze.ParamNotPassedError(msg)
            permitted_operators = self.conditions_operators.get(
                condition.get("condition"),
            )
            if permitted_operators is None:
                msg = f"Unknown condition: {condition.get('condition')}"
                raise ze.ParamNotPassedError(msg)
            if operator not in permitted_operators:
                msg = (
                    f"You may not use the '{operator}' operator when "
                    f"selecting the '{condition.get('condition')}' condition. \n"
                    f"Allowed operators: {', '.join(permitted_operators)}"
                )
                raise ze.ParamNotPassedError(msg)


__all__ = ["SavedSearch"]
