from pydantic import ValidationError
from fhir_batch_repository import ImmunizationBatchRepository
from models.errors import CustomValidationError
from models.fhir_immunization import ImmunizationValidator
from models.errors import MandatoryError


class ImmunizationBatchService:
    def __init__(
        self,
        immunization_repo: ImmunizationBatchRepository,
        validator: ImmunizationValidator = ImmunizationValidator(),
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
        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        return self.immunization_repo.create_immunization(
            immunization, supplier_system, vax_type, table, is_present
        )

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
        try:
            self.validator.validate(immunization)
        except (ValidationError, ValueError, MandatoryError) as error:
            raise CustomValidationError(message=str(error)) from error

        return self.immunization_repo.update_immunization(
            immunization, supplier_system, vax_type, table, is_present
        )

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
        return self.immunization_repo.delete_immunization(
            immunization, supplier_system, vax_type, table, is_present
        )
