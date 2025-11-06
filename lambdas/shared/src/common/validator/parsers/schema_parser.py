"""
Parses and manages schema configurations containing FHIR or csv transformation expressions.

Designed to work with JSON schema structures loaded directly into memory
suitable for caching systems like ElastiCache.

Example:
    >>> schema = {
    ...     "expressions": [
    ...         {"expression": "LOOKUP", "field": "route"},
    ...         {"expression": "KEYCHECK", "field": "site"}
    ...     ]
    ... }
    >>> parser = SchemaParser()
    >>> parser.parse_schema(schema)
    >>> parser.expression_count()
    >>> parser.get_expression(0)
    {'expression': 'LOOKUP', 'field': 'route'}
"""


class SchemaParser:
    def __init__(self) -> None:
        """Initializes empty schema and expression containers."""
        self.schema_file = {}
        self.expressions = {}

    def parse_schema(self, schema_file: dict) -> None:
        """
        Loads a schema definition (JSON/dict) and extracts expressions.
        """
        self.schema_file = schema_file
        self.expressions = self.schema_file["expressions"]

    def expression_count(self) -> int:
        """Returns the number of expressions containing the 'expression' key."""
        return sum([1 for d in self.expressions if "expression" in d])

    def get_expressions(self) -> list[dict]:
        """Returns all parsed expressions."""
        return self.expressions

    def get_expression(self, expression_number: int) -> dict:
        """Returns a specific expression by its index."""
        return self.expressions[expression_number]
