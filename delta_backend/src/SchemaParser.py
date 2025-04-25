# Schema Parser
# Moved from file loading to JSON string better for elasticache


class SchemaParser:
    # parser variables
    SchemaFile = {}
    Conversions = {}

    def parseSchema(self, schemaFile):  # changed to accept JSON better for cache
        self.schema_file = schemaFile
        self.Conversions = self.schema_file["conversions"]

    def conversionCount(self):
        count = 0
        count = sum([1 for d in self.Conversions if "conversion" in d])
        return count

    def getConversions(self):
        return self.Conversions

    def getConversion(self, conversionNumber):
        conversion = self.Conversions[conversionNumber]
        return conversion
