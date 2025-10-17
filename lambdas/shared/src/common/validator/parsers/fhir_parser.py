# FHIR JSON importer and data access
import json


class FHIRParser:
    # parser variables
    def __init__(self):
        self.fhir_resource = {}

    # -------------------------------------------
    # File Management
    # used for files
    def parse_fhir_file(self, fhir_file_name):
        with open(fhir_file_name) as json_file:
            self.fhir_resource = json.load(json_file)

    # used for JSON FHIR Resource data
    def parse_fhir_data(self, fhir_data):
        self.fhir_resource = fhir_data

    # ------------------------------------------------
    # Scan and Identify
    # scan for a key name or a value
    def _scan_values_for_match(self, parent, match_value):
        try:
            for key in parent:
                if parent[key] == match_value:
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
                    if (parent[index][key] == field_list[1]) or (key == field_list[1]):
                        node_id = index
                        break
                    else:
                        if self._scan_values_for_match(parent[index][key], field_list[1]):
                            node_id = index
                            break
                index += 1
        except Exception:
            return ""
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
                result = ""
        return result

    # locate a value for a key
    def _scan_for_value(self, fhir_fields):
        field_list = fhir_fields.split("|")
        # get root field before we iterate
        rootfield = self.fhir_resource[field_list[0]]
        del field_list[0]
        try:
            for field in field_list:
                if field.startswith("#"):
                    rootfield = self._locate_list_id(rootfield, field)  # check here for default index??
                else:
                    rootfield = self._get_node(rootfield, field)
        except Exception:
            rootfield = ""
        return rootfield

    # get the value list for a key
    def get_key_value(self, field_name):
        value = []
        try:
            response_value = self._scan_for_value(field_name)
        except Exception:
            response_value = ""

        value.append(response_value)
        return value

    # get the value list for a key
    def get_key_single_value(self, field_name):
        value = ""
        try:
            response_value = self._scan_for_value(field_name)
        except Exception:
            response_value = ""

        value = response_value
        return value
