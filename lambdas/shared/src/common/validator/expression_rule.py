from common.validator.constants.constants import Constants


def expression_rule_per_field(expression_type: str) -> dict:
    match expression_type:
        case "NHS_NUMBER":
            return {"defined_length": Constants.NHS_NUMBER_LENGTH, "spaces_allowed": False}
        case "PERSON_NAME":
            return {
                "elements_are_strings": True,
                "array_max_length": 5,
                "max_length": Constants.PERSON_NAME_ELEMENT_MAX_LENGTH,
            }
        case "PERSON_SURNAME":
            return {"max_length": Constants.PERSON_NAME_ELEMENT_MAX_LENGTH}
        case "GENDER":
            return {"predefined_values": Constants.GENDERS}
        case _:
            raise ValueError(f"Expression rule not found for type: {expression_type}")
