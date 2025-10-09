# FHIR JSON importer and data access
import json


class FHIRParser:
    # parser variables
    def __init__(self):
        self.FHIRResource = {}

    # -------------------------------------------
    # File Management
    # used for files
    def parse_fhir_file(self, fhir_file_name):
        with open(fhir_file_name, 'r') as json_file:
            self.FHIRResource = json.load(json_file)

    # used for JSON FHIR Resource data
    def parse_fhir_data(self, fhir_data):
        self.FHIRResource = fhir_data

    # ------------------------------------------------
    # Scan and Identify
    # scan for a key name or a value
    def _scan_values_for_match(self, parent, match_value):
        try:
            for key in parent:
                if (parent[key] == match_value):
                    return True
            return False
        except Exception:
            return False

    # locate an index for an item in a list
    def _locate_list_id(self, parent, locator):
        field_list = locator.split(":")
        node_id = 0
        index = 0
        try:
            while index < len(parent):
                for key in parent[index]:
                    if ((parent[index][key] == field_list[1]) or (key == field_list[1])):
                        node_id = index
                        break
                    else:
                        if self._scan_values_for_match(parent[index][key], field_list[1]):
                            node_id = index
                            break
                index += 1
        except Exception:
            return ''
        return parent[node_id]

    # identify a node in the FHIR data
    def _get_node(self, parent, child):
        # check for indices
        try:
            result = parent[child]
        except Exception:
            try:
                child = int(child)
                result = parent[child]
            except Exception:
                result = ''
        return result

    # locate a value for a key
    def _scanForValue(self, FHIRFields):
        fieldList = FHIRFields.split("|")
        # get root field before we iterate
        rootfield = self.FHIRResource[fieldList[0]]
        del fieldList[0]
        try:
            for field in fieldList:
                if (field.startswith("#")):
                    rootfield = self._locate_list_id(rootfield, field)  # check here for default index??
                else:
                    rootfield = self._get_node(rootfield, field)
        except Exception:
            rootfield = ''
        return rootfield

    # get the value list for a key
    def getKeyValue(self, fieldName):
        value = []
        try:
            responseValue = self._scanForValue(fieldName)
        except Exception:
            responseValue = ''

        value.append(responseValue)
        return value

    # get the value list for a key
    def getKeySingleValue(self, fieldName):
        value = ''
        try:
            responseValue = self._scanForValue(fieldName)
        except Exception:
            responseValue = ''

        value = responseValue
        return value
