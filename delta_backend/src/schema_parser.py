# Schema Parser
# Moved from file loading to JSON string better for elasticache


class SchemaParser:
    # parser variables
    schema_file = {}
    conversions = {}

    def parseSchema(self, schema_file):  # changed to accept JSON better for cache
        self.schema_file = schema_file
        self.conversions = self.schema_file["conversions"]

    def get_conversions(self):
        return self.conversions
