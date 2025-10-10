# Schema Parser
# Moved from file loading to JSON string better for elasticache


class SchemaParser:
    def __init__(self):
        # parser variables
        self.schema_file = {}
        self.expressions = {}

    def parse_schema(self, schema_file):  # changed to accept JSON better for cache
        self.schema_file = schema_file
        self.expressions = self.schema_file['expressions']

    def expression_count(self):
        count = 0
        count = sum([1 for d in self.expressions if 'expression' in d])
        return count

    def get_expressions(self):
        return self.expressions

    def get_expression(self, expression_number):
        expression = self.expressions[expression_number]
        return expression
