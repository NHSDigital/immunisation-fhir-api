from filter import Filter


def handle_s_flag(imms, patient):
    """
    See https://nhsd-confluence.digital.nhs.uk/pages/viewpage.action?pageId=758110223 for details.
    Checks if the patient has a restricted flag, and returns the imms resource with the appropriate filtering
    applied where necessary.
    NOTE: the term 's_flag' is not found in the PDS response. Instead we are searching for a code of
    'R' for RESTRICTED in the meta.security field.
    """

    patient_is_restricted = False

    # NOTE: meta.security is currently restricted to max length of 1 according to PDS, however we are looping
    # through all of the items in meta.security for safety in case PDS ever start sending more than one security item.
    for item in patient["meta"]["security"]:
        if str.upper(item["code"]) == "R":
            patient_is_restricted = True
            break

    return Filter.s_flag(imms) if patient_is_restricted else imms
