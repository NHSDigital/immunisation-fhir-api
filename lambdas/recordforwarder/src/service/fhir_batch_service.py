from common.models.errors import CustomValidationError, MandatoryError
from common.models.fhir_immunization import ImmunizationValidator
from repository.fhir_batch_repository import ImmunizationBatchRepository

IMMUNIZATION_VALIDATOR = ImmunizationValidator()

TPP_V2_SUPPLIER_IDENTIFIER_SYSTEM = "YGA"
TPP_V5_SUPPLIER_IDENTIFIER_SYSTEM = "https://tpp-uk.com/Id/ve/vacc"
EMIS_V2_SUPPLIER_IDENTIFIER_SYSTEM = "YGJ"
EMIS_V5_SUPPLIER_IDENTIFIER_SYSTEM = "https://emishealth.com/identifiers/vacc"


def uplift_legacy_identifier(immunization: dict):
    # This code the above constants can be safely removed once DPS carries out it's data migration to update legacy
    # identifiers as it should become redundant. However, it may be worth keeping in case legacy format identifiers are
    # received for some reason. Please see issue VED-904 for more information.
    identifier = immunization.get("identifier")

    if identifier is None or len(identifier) == 0:
        # Return here to allow validation to raise appropriate error
        return

    identifier_system = immunization.get("identifier")[0].get("system")

    if identifier_system == TPP_V2_SUPPLIER_IDENTIFIER_SYSTEM:
        immunization["identifier"][0]["system"] = TPP_V5_SUPPLIER_IDENTIFIER_SYSTEM

    if identifier_system == EMIS_V2_SUPPLIER_IDENTIFIER_SYSTEM:
        immunization["identifier"][0]["system"] = EMIS_V5_SUPPLIER_IDENTIFIER_SYSTEM


class ImmunizationBatchService:
    def __init__(
        self,
        immunization_repo: ImmunizationBatchRepository,
        validator: ImmunizationValidator = IMMUNIZATION_VALIDATOR,
    ):
        self.immunization_repo = immunization_repo
        self.validator = validator

    def create_immunization(
        self,
        immunization: any,
        supplier_system: str,
        vax_type: str,
        table: any,
        is_present: bool,
    ):
        """
        Creates an Immunization if it does not exits and return the ID back if successful.
        Exception will be raised if resource exits. Multiple calls to this method won't change
        the record in the database.
        """

        # TODO: Remove after DPS data migration to new identifiers
        uplift_legacy_identifier(immunization)

        try:
            self.validator.validate(immunization)
        except (ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        return self.immunization_repo.create_immunization(immunization, supplier_system, vax_type, table, is_present)

    def update_immunization(
        self,
        immunization: any,
        supplier_system: str,
        vax_type: str,
        table: any,
        is_present: bool,
    ):
        """
        Updates an Immunization if it exists and return the ID back if successful.
        Exception will be raised if resource didn't exist.Multiple calls to this method won't change
        the record in the database.
        """

        # TODO: Remove after DPS data migration to new identifiers
        uplift_legacy_identifier(immunization)

        try:
            self.validator.validate(immunization)
        except (ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        return self.immunization_repo.update_immunization(immunization, supplier_system, vax_type, table, is_present)

    def delete_immunization(
        self,
        immunization: any,
        supplier_system: str,
        vax_type: str,
        table: any,
        is_present: bool,
    ):
        """
        Delete an Immunization if it exists and return the ID back if successful.
        Exception will be raised if resource didn't exist.Multiple calls to this method won't change
        the record in the database.
        """

        # TODO: Remove after DPS data migration to new identifiers
        uplift_legacy_identifier(immunization)

        return self.immunization_repo.delete_immunization(immunization, supplier_system, vax_type, table, is_present)
