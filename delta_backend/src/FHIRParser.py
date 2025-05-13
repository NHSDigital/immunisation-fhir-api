# FHIR JSON importer and data access
import json
import jq
from utils import is_valid_simple_snomed

class FHIRParser:
    # parser variables
    FHIRFile = {}

    # used for JSON data
    def parseFHIRData(self, fhirData):
        self.FHIRFile = json.loads(fhirData) if isinstance(fhirData, str) else fhirData


    def _validate_expression_rule(self, expression_type, expression_rule, key_value_pair):
        """
        Applies expression rules for filtering key-value pairs during searches.

        This method provides a flexible foundation for implementing various filtering 
        or validation rules, enabling more dynamic and configurable search behavior. 
        While it currently supports only SNOMED code validation, the structure opens 
        the door to applying a wide range of expression rules in the future.

        For example, when processing a list of items, this method helps determine 
        which item(s) satisfy specific criteria based on the logic defined by the 
        expression type and rule.
        """
        if expression_type == "SNOMED" and expression_rule == "validate-code":
            if key_value_pair.get("code"):
                return is_valid_simple_snomed(key_value_pair["code"])
        
        return True
        
    # scan for a key name or a value
    def _scanValuesForMatch(self, parent, matchValue):
        try:
            for key in parent:
                if parent[key] == matchValue:
                    return True
            return False
        except:
            return False

    # locate an index for an item in a list
    def _locateListId(self, parent, locator, expression_type, expression_rule: str = ""):
        fieldList = locator.split(":", 1)
        nodeId = 0
        index = 0
        try:
            while index < len(parent):
                for key, value in parent[index].items():
                    if (
                        (value == fieldList[1] or key == fieldList[1])
                        and self._validate_expression_rule(expression_type, expression_rule, parent[index])
                    ):
                        nodeId = index
                        break
                    else:
                        if self._scanValuesForMatch(value, fieldList[1]):
                            nodeId = index
                            break
                index += 1
        except:
            return ""
        return parent[nodeId]

    # identify a node in the FHIR data
    def _getNode(self, parent, child):
        # check for indices
        try:
            result = parent[child]
        except:
            try:
                child = int(child)
                result = parent[child]
            except:
                result = ""
        return result

    # locate a value for a key
    def _scanForValue(self, FHIRFields, expression_type, expression_rule: str = ""):
        fieldList = FHIRFields.split("|")
        # get root field before we iterate
        rootfield = self.FHIRFile[fieldList[0]]
        del fieldList[0]
        try:
            for field in fieldList:
                if field.startswith("#"):
                    rootfield = self._locateListId(rootfield, field, expression_type, expression_rule)  # check here for default index??
                else:
                    rootfield = self._getNode(rootfield, field)
        except:
            rootfield = ""
        return rootfield

    # get the value for a key
    def getKeyValue(self, fieldName, flatFieldName: str = "", expression_type: str = "", expression_rule: str = ""):
        value = []
        try:
            if expression_type == "JQ":
                responseValue = self._extract_with_jq(fieldName, expression_rule)
            else:
                responseValue = self._scanForValue(fieldName, expression_type, expression_rule)
        except:
            responseValue = ""

        value.append(responseValue)
        
        return value
    
    def _extract_with_jq(self, jq_expr_str, expression_rule):
        try:
            result = jq.compile(jq_expr_str).input(self.FHIRFile).first()
            return result if result is not None else ""
        except Exception as e:
            # Optional: log or handle error
            return ""
