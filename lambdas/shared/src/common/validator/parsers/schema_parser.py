# Schema Parser
# Moved from file loading to JSON string better for elasticache 

class SchemaParser:
    #parser variables
    SchemaFile = {}
    Expressions = {}

    def parseSchema(self, schemaFile): # changed to accept JSON better for cache
            self.SchemaFile = schemaFile
            self.Expressions = self.SchemaFile['expressions']

 
    def expressionCount(self):
        count = 0
        count = sum([1 for d in self.Expressions if 'expression' in d])
        return count
    
    
    def getExpressions(self):
         return self.Expressions
    

    def getExpression(self, expressionNumber):
        expression = self.Expressions[expressionNumber]
        return expression