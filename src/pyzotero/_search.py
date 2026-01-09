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
        self.zinstance = zinstance
        self.searchkeys = ("condition", "operator", "value")
        # always exclude these fields from zotero.item_keys()
        self.excluded_items = (
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
            "A": (self.operators["true"], self.operators["false"]),
            "B": (self.operators["any"], self.operators["all"]),
            "C": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["contains"],
                self.operators["doesNotContain"],
            ),
            "D": (self.operators["is"], self.operators["isNot"]),
            "E": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["isBefore"],
                self.operators["isInTheLast"],
            ),
            "F": (self.operators["contains"], self.operators["doesNotContain"]),
            "G": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["contains"],
                self.operators["doesNotContain"],
                self.operators["isLessThan"],
                self.operators["isGreaterThan"],
            ),
            "H": (
                self.operators["is"],
                self.operators["isNot"],
                self.operators["beginsWith"],
            ),
            "I": (self.operators["is"]),
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
        ###########
        # ALIASES #
        ###########
        # aliases for numberfield
        pagefields = (
            "pages",
            "numPages",
            "numberOfVolumes",
            "section",
            "seriesNumber",
            "issue",
        )
        for pf in pagefields:
            self.conditions_operators[pf] = self.conditions_operators.get("numberfield")
        # aliases for datefield
        datefields = ("accessDate", "date", "dateDue", "accepted")
        for df in datefields:
            self.conditions_operators[df] = self.conditions_operators.get("datefield")
        # aliases for field - this makes a blocking API call unless item types have been cached
        item_fields = [
            itm["field"]
            for itm in self.zinstance.item_fields()
            if itm["field"] not in set(self.excluded_items)
        ]
        for itf in item_fields:
            self.conditions_operators[itf] = self.conditions_operators.get("field")

    def _validate(self, conditions: list[dict]) -> None:
        """Validate saved search conditions.

        Raises an error if any contain invalid operators.
        """
        allowed_keys = set(self.searchkeys)
        operators_set = set(self.operators.keys())
        for condition in conditions:
            if set(condition.keys()) != allowed_keys:
                msg = f"Keys must be all of: {', '.join(self.searchkeys)}"
                raise ze.ParamNotPassedError(msg)
            if condition.get("operator") not in operators_set:
                msg = f"You have specified an unknown operator: {condition.get('operator')}"
                raise ze.ParamNotPassedError(msg)
            # dict keys of allowed operators for the current condition
            permitted_operators = self.conditions_operators.get(
                condition.get("condition"),
            )
            if permitted_operators is None:
                msg = f"Unknown condition: {condition.get('condition')}"
                raise ze.ParamNotPassedError(msg)
            # transform these into values
            permitted_operators_list = {
                op_value
                for op in permitted_operators
                if (op_value := self.operators.get(op)) is not None
            }
            if condition.get("operator") not in permitted_operators_list:
                msg = (
                    f"You may not use the '{condition.get('operator')}' operator when "
                    f"selecting the '{condition.get('condition')}' condition. \n"
                    f"Allowed operators: {', '.join(list(permitted_operators_list))}"
                )
                raise ze.ParamNotPassedError(msg)


__all__ = ["SavedSearch"]
