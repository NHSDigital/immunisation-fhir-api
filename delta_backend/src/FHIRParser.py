# FHIR JSON importer and data access
import json


class FHIRParser:
    # parser variables
    FHIRFile = {}

    # used for JSON data
    def parseFHIRData(self, fhirData):
        self.FHIRFile = json.loads(fhirData) if isinstance(fhirData, str) else fhirData

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
    def _locateListId(self, parent, locator):
        fieldList = locator.split(":")
        nodeId = 0
        index = 0
        try:
            while index < len(parent):
                for key in parent[index]:
                    if (parent[index][key] == fieldList[1]) or (key == fieldList[1]):
                        nodeId = index
                        break
                    else:
                        if self._scanValuesForMatch(parent[index][key], fieldList[1]):
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
    def _scanForValue(self, FHIRFields):
        fieldList = FHIRFields.split("|")
        # get root field before we iterate
        rootfield = self.FHIRFile[fieldList[0]]
        del fieldList[0]
        try:
            for field in fieldList:
                if field.startswith("#"):
                    rootfield = self._locateListId(rootfield, field)  # check here for default index??
                else:
                    rootfield = self._getNode(rootfield, field)
        except:
            rootfield = ""
        return rootfield

    # get the value for a key
    def getKeyValue(self, fieldName):
        value = []
        try:
            responseValue = self._scanForValue(fieldName)
        except:
            responseValue = ""

        value.append(responseValue)
        return value
