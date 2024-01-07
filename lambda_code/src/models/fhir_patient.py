"""Patient FHIR R4B validator"""
from fhir.resources.R4B.patient import Patient
from models.patient_pre_validators import PatientPreValidators


class PatientValidator:
    """
    Validate the patient record against the NHS specific validators and Patient
    FHIR profile
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def pre_validate_name(cls, values: dict) -> dict:
        """Pre-validate that, if name exists, then it is an array of length 1"""
        try:
            name = values["name"]
            PatientPreValidators.name(name)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_name_given(cls, values: dict) -> dict:
        """
        Pre-validate that, if name[0] -> given (person_forename) exists, then it is a
        an array containing a single non-empty string
        """
        try:
            name_given = values["name"][0]["given"]
            PatientPreValidators.name_given(name_given)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_name_family(cls, values: dict) -> dict:
        """
        Pre-validate that, if name[0] -> family (person_surname) exists,
        then it is a non-empty string
        """

        try:
            name_family = values["name"][0]["family"]
            PatientPreValidators.name_family(name_family)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_birth_date(cls, values: dict) -> dict:
        """
        Pre-validate that, if birthDate (person_DOB) exists, then it is a string in the format
        YYYY-MM-DD, representing a valid date
        """

        try:
            birth_date = values["birthDate"]
            PatientPreValidators.birth_date(birth_date)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_gender(cls, values: dict) -> dict:
        """
        Pre-validate that, if gender (person_gender_code) exists, then it is a string, which is one
        of the following: male, female, other, unknown
        """

        try:
            gender = values["gender"]
            PatientPreValidators.gender(gender)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_address(cls, values: dict) -> dict:
        """Pre-validate that, if address exists, then it is an array of length 1"""
        try:
            address = values["address"]
            PatientPreValidators.address(address)
        except KeyError:
            pass

        return values

    @classmethod
    def pre_validate_address_postal_code(cls, values: dict) -> dict:
        """
        Pre-validate that, if  address -> postalCode  (person_postcode) exists, is a non-empty
        string, separated into two parts by a single space
        """

        try:
            address_postal_code = values["address"][0]["postalCode"]
            PatientPreValidators.address_postal_code(address_postal_code)
        except KeyError:
            pass

        return values

    def add_custom_root_validators(self):
        """Add custom NHS validators to the model"""
        Patient.add_root_validator(self.pre_validate_name, pre=True)
        Patient.add_root_validator(self.pre_validate_name_given, pre=True)
        Patient.add_root_validator(self.pre_validate_name_family, pre=True)
        Patient.add_root_validator(self.pre_validate_birth_date, pre=True)
        Patient.add_root_validator(self.pre_validate_gender, pre=True)
        Patient.add_root_validator(self.pre_validate_address, pre=True)
        Patient.add_root_validator(self.pre_validate_address_postal_code, pre=True)

    def validate(self, json_data) -> Patient:
        """Generate the Patient model from the JSON data"""
        return Patient.parse_obj(json_data)
