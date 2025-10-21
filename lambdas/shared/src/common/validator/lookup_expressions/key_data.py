"""
Stores predefined code lists and checks if a given code
exists in one of them by using KEYCHECK expressions to validate whether a code
(field value) is part of the Procedure, Organisation, Site,
or Route lists.

Attributes:
    procedure - list of valid medical procedure codes
    organisation - list of valid organisation codes.
    site - list of valid body site or anatomical location codes
    route - list of valid administration routes (e.g., oral, nasal, intramuscular)

Example:
    >>> key_data = KeyData()
    >>> key_data.findKey("Site", "368208006")
    True
"""


class KeyData:
    def __init__(self):
        """Initializes code lists for Procedure, Organisation, Site, and Route."""

        self.procedure: list[str] = ["956951000000104"]
        self.organisation: list[str] = ["RJ1", "RJC02"]
        self.site: list[str] = [
            "368208006",
            "279549004",
            "74262004",
            "368209003",
            "723979003",
            "61396006",
            "723980000",
            "11207009",
            "420254004",
        ]

        self.route: list[str] = [
            "54471007",
            "372449004",
            "372450004",
            "372451000",
            "372452007",
            "404820008",
            "18246711000001107",
            "372453002",
            "372454008",
            "127490009",
            "372457001",
            "9191401000001100",
            "18682911000001103",
            "10334211000001103",
            "718329006",
            "18679011000001101",
            "34777511000001106",
            "372458006",
            "58100008",
            "12130007",
            "372459003",
            "418821007",
            "372460008",
            "372461007",
            "420719007",
            "19537211000001108",
            "372463005",
            "372464004",
            "372465003",
            "448077001",
            "38233211000001106",
            "372466002",
            "372467006",
            "78421000",
            "255559005",
            "372468001",
            "417255000",
            "38239002",
            "372469009",
            "372470005",
            "418586008",
            "72607000",
            "447122006",
            "62226000",
            "47625008",
            "420287000",
            "372471009",
            "418401004",
            "21856811000001103",
            "127491008",
            "9907001000001103",
            "46713006",
            "127492001",
            "418730005",
            "54485002",
            "26643006",
            "372473007",
            "10547007",
            "225691000001105",
            "9191501000001101",
            "372474001",
            "39338211000001108",
            "3323001000001107",
            "372475000",
            "11478901000001102",
            "419762003",
            "39337511000001107",
            "37161004",
            "11564311000001109",
            "418321004",
            "3594011000001102",
            "372476004",
            "34206005",
            "37839007",
            "419874009",
            "11564211000001101",
            "33770711000001104",
            "6064005",
            "45890007",
            "11479001000001107",
            "404815008",
            "90028008",
            "16857009",
        ]

    def findKey(self, key_source: str, field_value: str) -> bool:
        try:
            match key_source:
                case "Procedure":
                    return field_value in self.procedure
                case "Organisation":
                    return field_value in self.organisation
                case "Site":
                    return field_value in self.site
                case "Route":
                    return field_value in self.route
                case _:
                    return False
        except Exception:
            return False
        return False
