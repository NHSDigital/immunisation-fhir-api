import unittest

from common.validator.parsers.schema_parser import SchemaParser


class TestSchemaParser(unittest.TestCase):
    def test_parse_and_count_expressions(self):
        schema = {
            "expressions": [
                {"expression": "LOOKUP", "field": "route"},
                {"field": "no-op"},  # missing 'expression' should not be counted
                {"expression": "KEYCHECK", "field": "site"},
            ]
        }
        p = SchemaParser()
        p.parse_schema(schema)
        self.assertEqual(p.expression_count(), 2)

    def test_get_expression_by_index(self):
        schema = {
            "expressions": [
                {"expression": "A", "field": "x"},
                {"expression": "B", "field": "y"},
            ]
        }
        p = SchemaParser()
        p.parse_schema(schema)
        self.assertEqual(p.get_expression(0), {"expression": "A", "field": "x"})
        self.assertEqual(p.get_expression(1), {"expression": "B", "field": "y"})
        with self.assertRaises(IndexError):
            _ = p.get_expression(2)

    def test_get_expressions_returns_all(self):
        expressions = [
            {"expression": "A", "field": "x"},
            {"expression": "B", "field": "y"},
            {"field": "ignored"},
        ]
        p = SchemaParser()
        p.parse_schema({"expressions": expressions})
        self.assertEqual(p.get_expressions(), expressions)


if __name__ == "__main__":
    unittest.main()
