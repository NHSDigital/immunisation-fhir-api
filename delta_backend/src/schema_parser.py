# Schema Parser
# Moved from file loading to JSON string better for elasticache


class SchemaParser:
    # parser variables
    schema_file = {}
    conversions = {}

    def parseSchema(self, schema_file):  # changed to accept JSON better for cache
        self.schema_file = schema_file
        self.conversions = self.schema_file["conversions"]

    def conversionCount(self):
        count = 0
        count = sum([1 for d in self.conversions if "conversion" in d])
        return count

    def getConversions(self):
        return self.conversions

    def getConversion(self, conversion_number):
        conversion = self.conversions[conversion_number]
        return conversion
