from fhir.resources.immunization import Immunization as FHIRImmunization
from fhir.resources.immunization import (
    ImmunizationProtocolApplied as FHIRImmunizationProtocolApplied,
)
from models.FHIRUKImmunization import UKFHIRImmunization
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.humanname import HumanName as FHIRHumanName
from fhir.resources.address import Address as FHIRAddress
from fhir.resources.identifier import Identifier as FHIRIdentifier
from fhir.resources.practitioner import Practitioner as FHIRPractitioner
from fhir.resources.coding import Coding as FHIRCoding
from fhir.resources.extension import Extension as FHIRExtension
from fhir.resources.codeableconcept import CodeableConcept as FHIRCodeableConcept
from fhir.resources.organization import Organization as FHIROrganization
from fhir.resources.quantity import Quantity as FHIRQuantity
from fhir.resources.reference import Reference as FHIRReference
from fhir.resources.questionnaireresponse import (
    QuestionnaireResponse,
    QuestionnaireResponseItem,
)
from fhir.resources.questionnaireresponse import QuestionnaireResponseItemAnswer


def convert_to_fhir(immunization_model):

    uk_fhir_immunization = UKFHIRImmunization()
    snomed = "http://snomed.info/sct"
    fhir_patient = FHIRPatient(
        identifier=[
            FHIRIdentifier(
                system="https//fhir.nhs.uk/Id/nhs-number",
                value=immunization_model.NHS_NUMBER,
            )
        ],
        resource_type="Patient",
    )

    fhir_patient.name = [
        FHIRHumanName(
            family=immunization_model.PERSON_SURNAME,
            given=[immunization_model.PERSON_FORENAME],
        )
    ]
    fhir_patient.birthDate = immunization_model.PERSON_DOB
    fhir_patient.gender = immunization_model.PERSON_GENDER_CODE
    fhir_patient.address = [FHIRAddress(postalCode=immunization_model.PERSON_POSTCODE)]
    uk_fhir_immunization.patient = fhir_patient
    # Create a Coding for the vaccine code
    vaccine_code_coding = FHIRCoding(
        system=snomed,
        code=immunization_model.VACCINE_PRODUCT_CODE,
        display=immunization_model.VACCINE_PRODUCT_TERM,
    )

    # Create a CodeableConcept for the vaccine code
    vaccine_codeable_concept = FHIRCodeableConcept(coding=[vaccine_code_coding])
    uk_fhir_immunization.immunization = FHIRImmunization(
        status=immunization_model.ACTION_FLAG,
        occurrenceDateTime=immunization_model.DATE_AND_TIME,
        patient=FHIRReference(reference=f"Patient/{immunization_model.NHS_NUMBER}"),
        vaccineCode=vaccine_codeable_concept,
    )
    contained_questionnaire_response = QuestionnaireResponse(
        resourceType="QuestionnaireResponse",
        status="completed",
        questionnaire=f"Questionnaire/{1}",
        item=[
            QuestionnaireResponseItem(
                linkId="SiteCode",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            system=immunization_model.SITE_CODE_TYPE_URI,
                            code=immunization_model.SITE_CODE,
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="SiteName",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(code=immunization_model.SITE_NAME)
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="NhsNumberStatus",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            code=immunization_model.NHS_NUMBER_STATUS_INDICATOR_CODE,
                            display=immunization_model.NHS_NUMBER_STATUS_INDICATOR_DESCRIPTION,
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="LocalPatient",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            system=immunization_model.LOCAL_PATIENT_URI,
                            code=immunization_model.LOCAL_PATIENT_ID,
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="Consent",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            display=immunization_model.CONSENT_FOR_TREATMENT_DESCRIPTION,
                            code=immunization_model.CONSENT_FOR_TREATMENT_CODE,
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="CareSetting",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            display=immunization_model.CARE_SETTING_TYPE_DESCRIPTION,
                            code=immunization_model.CARE_SETTING_TYPE_CODE,
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="IpAddress",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(code=immunization_model.IP_ADDRESS)
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="UserId",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(code=immunization_model.USER_ID)
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="UserName",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(code=immunization_model.USER_NAME)
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="UserEmail",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(code=immunization_model.USER_EMAIL)
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="SubmittedTimeStamp",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            code=immunization_model.SUBMITTED_TIMESTAMP
                        )
                    )
                ],
            ),
            QuestionnaireResponseItem(
                linkId="ReduceValidation",
                answer=[
                    QuestionnaireResponseItemAnswer(
                        valueCoding=FHIRCoding(
                            code=immunization_model.REDUCE_VALIDATION_CODE,
                            display=immunization_model.REDUCE_VALIDATION_REASON,
                        )
                    )
                ],
            ),
        ],
    )

    uk_fhir_immunization.immunization.contained = [contained_questionnaire_response]
    uk_fhir_immunization.immunization.identifier = [
        FHIRIdentifier(
            value=immunization_model.UNIQUE_ID, system=immunization_model.UNIQUE_ID_URI
        )
    ]
    performer_identifier = [
        FHIRIdentifier(
            system=immunization_model.PERFORMING_PROFESSIONAL_BODY_REG_URI,
            value=immunization_model.PERFORMING_PROFESSIONAL_BODY_REG_CODE,
            type=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        display=immunization_model.SDS_JOB_ROLE_NAME,
                    )
                ]
            ),
        )
    ]

    performer_name = [
        FHIRHumanName(
            family=immunization_model.PERFORMING_PROFESSIONAL_SURNAME,
            given=[immunization_model.PERFORMING_PROFESSIONAL_FORENAME],
        )
    ]
    # Not populating it directly with FHIRImmunizationPerformer becasue it is
    # reference to practitioner but we want actual Practitioner content
    uk_fhir_immunization.actor = FHIRPractitioner(
        resource_type="Practitioner",
        identifier=performer_identifier, #Populate only if its only None, test it
        name=performer_name,  #Populate only if its only None, test it
    )
    uk_fhir_immunization.immunization.primarySource = immunization_model.PRIMARY_SOURCE
    extension1 = FHIRExtension(
        valueCodeableConcept=FHIRCodeableConcept(
            coding=[
                FHIRCoding(
                    system=snomed,
                    code=immunization_model.VACCINATION_PROCEDURE_CODE,
                    display=immunization_model.VACCINATION_PROCEDURE_TERM,
                )
            ]
        ),
        url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
    )
    extension2 = FHIRExtension(
        valueCodeableConcept=FHIRCodeableConcept(
            coding=[
                FHIRCoding(
                    system=snomed,
                    code=immunization_model.VACCINATION_SITUATION_CODE,
                    display=immunization_model.VACCINATION_SITUATION_TERM,
                )
            ]
        ),
        url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
    )
    uk_fhir_immunization.immunization.extension = [extension1, extension2]

    # Check if status is empty,
    if  uk_fhir_immunization.immunization.status =="empty":
        uk_fhir_immunization.immunization.status = immunization_model.NOT_GIVEN
    uk_fhir_immunization.immunization.statusReason = FHIRCodeableConcept(
        coding=[
            FHIRCoding(
                system=snomed,
                code=immunization_model.REASON_NOT_GIVEN_CODE,
                display=immunization_model.REASON_NOT_GIVEN_TERM,
            )
        ]
    )

    uk_fhir_immunization.immunization.protocolApplied = [
        FHIRImmunizationProtocolApplied(
            targetDisease=[
                FHIRCodeableConcept(
                    coding=[FHIRCoding(code=immunization_model.VACCINE_CUSTOM_LIST)]
                )
            ],
            doseNumber=immunization_model.DOSE_SEQUENCE,
        )
    ]

    # Create an Organization instance
    uk_fhir_immunization.manufacturer = FHIROrganization(
        resource_type="Organization", name=immunization_model.VACCINE_MANUFACTURER
    )

    uk_fhir_immunization.immunization.lotNumber = immunization_model.BATCH_NUMBER
    uk_fhir_immunization.immunization.expirationDate = immunization_model.EXPIRY_DATE
    uk_fhir_immunization.immunization.site = FHIRCodeableConcept(
        coding=[
            FHIRCoding(
                system=snomed,
                code=immunization_model.SITE_OF_VACCINATION_CODE,
                display=immunization_model.SITE_OF_VACCINATION_TERM,
            )
        ]
    )
    uk_fhir_immunization.immunization.route = FHIRCodeableConcept(
        coding=[
            FHIRCoding(
                system=snomed,
                code=immunization_model.ROUTE_OF_VACCINATION_CODE,
                display=immunization_model.ROUTE_OF_VACCINATION_TERM,
            )
        ]
    )
    uk_fhir_immunization.immunization.doseQuantity = FHIRQuantity(
        value=immunization_model.DOSE_AMOUNT,
        code=immunization_model.DOSE_UNIT_CODE,
        unit=immunization_model.DOSE_UNIT_TERM,
        system="http://unitsofmeasure.org",
    )

    uk_fhir_immunization.immunization.location = FHIRReference(
        identifier=FHIRIdentifier(
            value=immunization_model.LOCATION_CODE,
            system=immunization_model.LOCATION_CODE_TYPE_URI,
        )
    )
    uk_fhir_immunization.recorded = immunization_model.RECORDED_DATE
    uk_fhir_immunization.reportOrigin = FHIRCodeableConcept(
        text=immunization_model.REPORT_ORIGIN
    )
    uk_fhir_immunization.reasonCode = [
        FHIRCodeableConcept(
            coding=[
                FHIRCoding(
                    code=immunization_model.INDICATION_CODE,
                    display=immunization_model.INDICATION_TERM,
                )
            ]
        )
    ]

    return uk_fhir_immunization
