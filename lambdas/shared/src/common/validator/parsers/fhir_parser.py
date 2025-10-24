import json


class FHIRParser:
    def __init__(self):
        self.fhir_resources = {}

    # This opens a file with FHIR resource data
    def parse_fhir_file(self, fhir_file_name: str) -> None:
        with open(fhir_file_name) as json_file:
            self.fhir_resources = json.load(json_file)

    # This is used for JSON FHIR Resource data events
    def parse_fhir_data(self, fhir_data: dict) -> None:
        self.fhir_resources = fhir_data

    def _locate_fhir_item_in_dict(self, fhir_resource: dict, fhir_field: str) -> bool:
        """
        Checks whether a given FHIR field name or value exists in a FHIR dictionary.
         :param fhir_resource: The FHIR resource as a dictionary.
         :param fhir_field: The FHIR field name or value to search for.
         :return: True if the field name or value matches a key item in the resource, False otherwise.
        """
        try:
            for key in fhir_resource:
                if fhir_resource[key] == fhir_field:
                    return True
            return False
        except Exception:
            return False

    def _locate_fhir_item_in_list(self, fhir_resource: list, fhir_field: str) -> dict:
        """
        Locates and returns the first FHIR item (dictionary) in a list that contains
        the specified FHIR field name or value.
        :param fhir_resource: The FHIR resource as a list of dictionaries.
        :param fhir_field: The FHIR field name or value to search for.
        :return: The first matching FHIR item (dictionary) if found, otherwise an empty string.
        """
        field_list = fhir_field.split(":")
        node_id = 0
        index = 0
        try:
            while index < len(fhir_resource):
                for key in fhir_resource[index]:
                    if (fhir_resource[index][key] == field_list[1]) or (key == field_list[1]):
                        node_id = index
                        break
                    else:
                        if self._locate_fhir_item_in_dict(fhir_resource[index][key], field_list[1]):
                            node_id = index
                            break
                index += 1
        except Exception:
            return ""
        return fhir_resource[node_id]

    # identify a node in the FHIR data
    def _extract_fhir_node_value(self, fhir_resource: dict | list, fhir_field_key: str) -> str:
        """
        Safely retrieves a value from a FHIR resource by key or index.
        :param fhir_resource: The FHIR resource, which can be a dictionary or a list.
        :param fhir_field_key: The key (string) or index (integer as string) to retrieve the value for.
        :return: The value associated with the key or index, or an empty string if not found.
        """
        try:
            result = fhir_resource[fhir_field_key]
        except Exception:
            try:
                child = int(fhir_field_key)
                result = fhir_resource[child]
            except Exception:
                result = ""
        return result

    def _resolve_fhir_path(self, fhir_field_path: str) -> str:
        """
        Resolves a FHIR value from a pipe-delimited FHIR path string.
        This function navigates through FHIR resources stored in `self.fhir_resources`
        using the provided path, which may include nested dictionaries or lists.
        Fields prefixed with "#" indicate list-based lookups.
        """
        field_list = fhir_field_path.split("|")

        # get root field before we iterate
        resource_per_field = self.fhir_resources[field_list[0]]
        del field_list[0]
        try:
            for field in field_list:
                if field.startswith("#"):
                    resource_per_field = self._locate_fhir_item_in_list(
                        resource_per_field, field
                    )  # check here for default index??
                else:
                    resource_per_field = self._extract_fhir_node_value(resource_per_field, field)
        except Exception:
            resource_per_field = ""
        return resource_per_field

    def get_fhir_value_list(self, field_path: str) -> list[str]:
        """
        Retrieves one or more values from a FHIR resource and returns them as a list.
        :param field_path: The FHIR field path to retrieve the values for.
        :return: A list of values found at the specified FHIR field path.
        """
        value = []
        try:
            response_value = self._resolve_fhir_path(field_path)
        except Exception:
            response_value = ""

        value.append(response_value)
        return value

    def get_fhir_value(self, field_path: str) -> str:
        """
        Retrieves a single value from a FHIR resource.
        :param field_path: The FHIR field path to retrieve the value for.
        :return: The value as a string, or an empty string if not found.
        """
        value = ""
        try:
            response_value = self._resolve_fhir_path(field_path)
        except Exception:
            response_value = ""

        value = response_value
        return value
