from marshmallow import Schema, fields, validate, validates_schema, validates,pre_load,post_load
from marshmallow.validate import Regexp
import re
from datetime import datetime
from typing import Union
from mappings import DiseaseCodes


class DiseaseCode:
    """Disease Codes"""
    covid_19 = DiseaseCodes.covid_19
    flu = DiseaseCodes.flu
    hpv = DiseaseCodes.hpv
    mumps = DiseaseCodes.mumps
    rubella= DiseaseCodes.rubella
    measles= DiseaseCodes.measles


    all_codes = {covid_19, flu, hpv, mumps,measles,rubella}


def validate_resource_type(value):
     if value != "Immunization":
        raise ValueError(f"expects resource type `Immunization`, but got {value}. Make sure resource type name is correct and right ModelClass has been chosen")
     

class Strictdate(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        if len(value) == 0:
            raise ValueError("expirationDate must be a valid date string in the format \"YYYY-MM-DD\"")  
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("The date is not valid. Must be in the format 'YYYY-MM-DD'")
        return date_obj
    
class StrictBoolean(fields.Field):
    def _deserializes(self, value, attr, data, **kwargs):
        if isinstance(value, bool):
            return value
        raise ValueError("primarySource must be a boolean")    

def valid_name(field_name):
    def _validate_given(name_list):
        for name in name_list:
            if 'given' in name and all(not given_name for given_name in name['given']):
                raise ValueError(f'{field_name} must be an array of non-empty strings')
    return  _validate_given

def valid_family(field_name):
    def _validate_family(name_list):
        for name in name_list:
            if 'family' in name and all(not family for family in name['family']):
                raise ValueError(f'{field_name} must be an array of non-empty strings')
    return  _validate_family
def validate_identifier(value):
    pattern = r"^[A-Z]{1}[0-9]{1}[A-Z]{1}[0-9]{1}[A-Z]{1}$"
    if not re.match(pattern, value):
        raise ValueError("performer[?(@.actor.type=='Organization')].actor.identifier.value must be in expected format" + " alpha-numeric-alpha-numeric-alpha (e.g X0X0X)")             
    

class NameSchema(Schema):
    family = fields.Str(required=True, error_messages={"required": "contained[?(@.resourceType=='Patient')].name[0].family is a mandatory field", "invalid": "contained[?(@.resourceType=='Patient')].name[0].family must be a string"})
    given = fields.List(fields.Str(), required=True, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].name[0].given must be an array"})
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('given')
    def validate_name_given_length(self, value):
        if len(value) != 1:
            if self.field_name == "Patient":
                raise ValueError("contained[?(@.resourceType=='Patient')].name[0].given must be an array of length 1")
            if self.field_name == 'Practitioner':
                raise ValueError("contained[?(@.resourceType=='Practitioner')].name[0].given must be an array of length 1")
            
class PracticinerNameSchema(Schema):
    family = fields.Str(required=False, error_messages={"invalid": "contained[?(@.resourceType=='Practitioner')].name[0].family must be a string"})
    given = fields.List(fields.Str(), required=False, error_messages={"invalid": "contained[?(@.resourceType=='Practitioner')].name[0].given must be an array"})
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('given')
    def validate_given_length(self, value):
        if len(value) != 1:
            if self.field_name == "Patient":
                raise ValueError("contained[?(@.resourceType=='Patient')].name[0].given must be an array of length 1")
            if self.field_name == 'Practitioner':
                raise ValueError("contained[?(@.resourceType=='Practitioner')].name[0].given must be an array of length 1")            


class AddressSchema(Schema):
    postalCode = fields.Str(required=True, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].address[0].postalCode must be a string"})
    @validates('postalCode')
    def validate_postcode_length(self, value):
        if len(value) == 0:
            raise ValueError("contained[?(@.resourceType=='Patient')].address[0].postalCode must be a non-empty string")
        if value.count(" ") != 1 or value.startswith(" ") or value.endswith(" "):
                raise ValueError("contained[?(@.resourceType=='Patient')].address[0].postalCode must contain a single space, " + "which divides the two parts of the postal code")
        if len(value.replace(" ", "")) > 8:
                raise ValueError("contained[?(@.resourceType=='Patient')].address[0].postalCode must be 8 or fewer characters (excluding spaces)")                          
        pattern = r'^[a-zA-Z]{1,2}([0-9]{1,2}|[0-9][a-zA-Z])\s*[0-9][a-zA-Z]{2}$'
        is_correct_format = re.match(pattern, value) is not None
        if not is_correct_format:
            raise ValueError("contained[?(@.resourceType=='Patient')].address[0].postalCode must be 8 or fewer characters (excluding spaces)")

    
class PractitionerSchema(Schema):
    resourceType = fields.Str(required=True,error_messages={"invalid": "contained[?(@.resourceType=='Practitioner')].resourceType must be a string"})
    id = fields.Str(required=True, error_messages={"required": "The contained Practitioner resource must have an 'id' field", "invalid": "contained[?(@.resourceType=='Practitioner')].id must be a string"})
    name = fields.List(fields.Nested(PracticinerNameSchema(field_name = "Practitioner")), error_messages={"invalid": "contained[?(@.resourceType=='Practitioner')].name must be an array"}, required=False, validate=[valid_name("contained[?(@.resourceType=='Practitioner')].name[0].given"),valid_family("contained[?(@.resourceType=='Practitioner')].name[0].family")])
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)
    
    @validates('name')
    def validate_given_length(self, value):
        if len(value) != 1:
                raise ValueError("contained[?(@.resourceType=='Practitioner')].name must be an array of length 1")
             
# Define the schema for the identifier
class IdentifierSchema(Schema):
    system = fields.Str(required=False, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].identifier[0].system must be a string"})
    value = fields.Str(required=False, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].identifier[0].value must be a string"})  

    
    @validates('system')
    def validate_identifier_system_length(self, value):
        if len(value) == 0:
           raise ValueError("contained[?(@.resourceType=='Patient')].identifier[0].system must be an array of non-empty strings")
        if value != "https://fhir.nhs.uk/Id/nhs-number":
           raise ValueError("contained[?(@.resourceType=='Patient')].identifier[0].system does not match")
        
    @validates('value')
    def validate_nhsnumber_length(self, value):
        is_mod11 = False
        if len(value) != 10:
            raise ValueError("contained[?(@.resourceType=='Patient')].identifier[0].value must be 10 characters")
        if value.isdigit() and len(value) == 10:
            # Create a reversed list of weighting factors
            weighting_factors = list(range(2, 11))[::-1]
            # Multiply each of the first nine digits by the weighting factor and add the results of each multiplication
            # together
            total = sum(int(digit) * weight for digit, weight in zip(value[:-1], weighting_factors))
            # Divide the total by 11 and establish the remainder and subtract the remainder from 11 to give the check digit.
            # If the result is 11 then a check digit of 0 is used. If the result is 10 then the NHS NUMBER is invalid and
            # not used.
            check_digit = 0 if (total % 11 == 0) else (11 - (total % 11))
            # Check the remainder matches the check digit. If it does not, the NHS NUMBER is invalid.
            is_mod11 = check_digit == int(value[-1])
            if is_mod11 is False:
                raise ValueError("contained[?(@.resourceType=='Patient')].identifier[0].value does not exists")
        else:
            raise ValueError("contained[?(@.resourceType=='Patient')].identifier[0].value does not exists")
    


class ContainedPatientSchema(Schema):
    resourceType = fields.Str(required=True, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].resourceType must be a string"}, validate=[validate.Equal("Patient")])
    id = fields.Str(required=True, error_messages={"invalid": "contained[?(@.resourceType=='Patient')].id must be a string"})
    identifier = fields.List(fields.Nested(IdentifierSchema), required=False,error_messages={"invalid": "contained[?(@.resourceType=='Patient')].identifier must be an array"})
    name = fields.List(fields.Nested(NameSchema(field_name = "Patient")), error_messages={"required": "contained[?(@.resourceType=='Patient')].name[0].family is a mandatory field","invalid": "contained[?(@.resourceType=='Patient')].name be an array"}, required=True, validate=[valid_name("contained[?(@.resourceType=='Patient')].name[0].given"), valid_family("contained[?(@.resourceType=='Patient')].name[0].family")])
    gender = fields.Str(required=True, error_messages={'required':"contained[?(@.resourceType=='Patient')].gender is a mandatory field", 'invalid':"contained[?(@.resourceType=='Patient')].gender must be a string"})
    birthDate = fields.Str(required=True,error_messages={'required':"contained[?(@.resourceType=='Patient')].birthDate is a mandatory field", 'invalid': "contained[?(@.resourceType=='Patient')].birthDate must be a string"})
    address = fields.List(fields.Nested(AddressSchema), required=True,error_messages={"invalid": "contained[?(@.resourceType=='Patient')].address must be an array"})
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('gender')
    def validate_gender_length(self, value):
        if len(value) == 0:
            raise ValueError("contained[?(@.resourceType=='Patient')].gender must be an array of length 1")
        if value not in ["male", "female", "other", "unknown"]:
            raise ValueError("Validation errors: contained[?(@.resourceType=='Patient')].gender must be one of the following: male, female, other, unknown")
    
    @validates('birthDate')
    def validate_birthdate_length(self, value):
         try:
            datetime.strptime(value, "%Y-%m-%d")
         except ValueError:
            raise ValueError("contained[?(@.resourceType=='Patient')].birthDate must be a valid date string in the format 'YYYY-MM-DD'")

    @validates('name')
    def validate_name_length(self, value):
        if len(value) != 1:
                raise ValueError("contained[?(@.resourceType=='Patient')].name must be an array of length 1")  

    @validates('address')
    def validate_address_length(self, value):
        if len(value) != 1:
                raise ValueError("contained[?(@.resourceType=='Patient')].address must be an array of length 1") 

    @validates('identifier')
    def validate_identifier_length(self, value):
        if len(value) != 1 or value == [{}]:
                raise ValueError("contained[?(@.resourceType=='Patient')].identifier must be an array of length 1")    


class protocolCodingSchema(Schema):
    system = fields.Str(required=True, error_messages={"required": "protocolApplied[0].targetDisease[*].coding[0].system is a mandatory field", "invalid": "protocolApplied[0].targetDisease[*].coding[0].system must be a string"})
    code = fields.Str(required=True, error_messages={"required": "protocolApplied[0].targetDisease[*].coding[0].code is a mandatory field", "invalid": "protocolApplied[0].targetDisease[*].coding[0].code must be a string"})
    display = fields.Str(required=True, error_messages={"required": "protocolApplied[0].targetDisease[*].coding[0].display is a mandatory field", "invalid": "protocolApplied[0].targetDisease[*].coding[0].display must be a string"})
    
    @validates('system')
    def validate_protocolCoding_schema_length(self, value):
        if len(value) == 0:
            raise ValueError("protocolApplied[0].targetDisease[*].coding[0].system must be a non-empty string")
        if value != "http://snomed.info/sct":
            raise ValueError("protocolApplied[0].targetDisease[*].coding[0].system.coding[0].system must be unique")
        

    @validates('code')
    def validate_code_length(self, value):
        if len(value) == 0:
            raise ValueError("protocolApplied[0].targetDisease[*].coding[0].code must be a non-empty string")

    @validates('code')
    def validate_code(self, value):
        if value not in DiseaseCode.all_codes and value != "":
            raise ValueError(f'[{value}] is not a valid combination of disease codes for this service')    
        
 
    @validates('display')
    def validate_display_length(self, value):
        if len(value) == 0:
            raise ValueError("protocolApplied[0].targetDisease[*].coding[0].display must be a non-empty string")                   
        
# Define the Coding schema
class CodingSchema(Schema):
    system = fields.Str(required=False)
    code = fields.Str(required=False)
    display = fields.Str(required=False)

    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)
    
    @validates('system')
    def validate_system_length(self, value):
        if len(value) == 0:
            raise ValueError(f"{self.field_name}.coding[?(@.system=='http://snomed.info/sct')] must be a non-empty string")
        if value != "http://snomed.info/sct":
            raise ValueError(f"{self.field_name}.coding[?(@.system=='http://snomed.info/sct')] must be unique")
        if not isinstance(value, str):
            raise ValueError(f"{self.field_name}.coding[?(@.system=='http://snomed.info/sct')] must be a string")

    @validates('code')
    def validate_code_length(self, value):
        if len(value) == 0:
            raise ValueError(f"{self.field_name}.coding[0].code must be a non-empty string")
        if not isinstance(value, str):
            raise ValueError(f"{self.field_name}.coding[0].code must be a string")
 
    @validates('display')
    def validate_display_length(self, value):
        if len(value) == 0:
            raise ValueError(f"{self.field_name}.coding[0].display must be a non-empty string")
        if not isinstance(value, str):
            raise ValueError(f"{self.field_name}.coding[0].display must be a string")


class ReasonCodingSchema(Schema):
    system = fields.Str(required=False, error_messages={"invalid": "reasoncode.coding[0].system must be a string"})
    code = fields.Str(required=False, error_messages={"invalid": "reasoncode.coding[0].code must be a string"})  

    @validates('system')
    def validate_system_length(self, value):
        if len(value) == 0:
            raise ValueError("reasoncode.coding[0].system must be a non-empty string")
        if value != "http://snomed.info/sct":
            raise ValueError("reasoncode.coding[0].system must be unique")
        
    @validates('code')
    def validate_code_length(self, value):
        if len(value) == 0:
            raise ValueError("reasoncode.coding[0].code must be a non-empty string")

# Define the Identifier schema
class MainIdentifierSchema(Schema):
    system = fields.Str(required=True, error_messages={"required":" identifier[0].system is a mandatory field","invalid":" identifier[0].system must be a string"})
    value = fields.Str(required=True, error_messages={"required":" identifier[0].value is a mandatory field", "invalid":"identifier[0].value must be a string"})
    
    @validates('system')
    def validate_system_length(self, value):
        if len(value) == 0:
            raise ValueError("identifier[0].system must be a non-empty string")
    
    @validates('value')
    def validate_identifier_schema_value_length(self, value):
        if len(value) == 0:
            raise ValueError("identifier[0].value must be a non-empty string")
        
# Define the CodeableConcept schema
class vaccineCodeableConceptSchema(Schema):
    
    coding = fields.List(fields.Nested(CodingSchema(field_name='vaccineCode')), required=False)
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) != 1 or value == [{}]:
            raise ValueError(f"{self.field_name}.coding array must have exactly one item.")        
        if not isinstance(value, list):
            raise ValueError(f"{self.field_name}.coding must be an array")

# Define the CodeableConcept schema
class siteCodeableConceptSchema(Schema):
    
    coding = fields.List(fields.Nested(CodingSchema(field_name='site')), required=False)
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) != 1 or value == [{}]:
            raise ValueError(f"{self.field_name}.coding array must have exactly one item.")        
        if not isinstance(value, list):
            raise ValueError(f"{self.field_name}.coding must be an array")

# Define the CodeableConcept schema
class routeCodeableConceptSchema(Schema):
    
    coding = fields.List(fields.Nested(CodingSchema(field_name='route')), required=False)
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) != 1 or value == [{}]:
            raise ValueError(f"{self.field_name}.coding array must have exactly one item.")        
        if not isinstance(value, list):
            raise ValueError(f"{self.field_name}.coding must be an array")

# Define the CodeableConcept schema
class ProtocolCodeableConceptSchema(Schema):
    
    coding = fields.List(fields.Nested(protocolCodingSchema), required=True,error_messages={"required": "protocolApplied[0].targetDisease[*].coding is a mandatory field"})
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) == 0 or value == [{}]:
            if self.field_name == 'protocolApplied':
                raise ValueError("protocolApplied[0].targetDisease[*].coding must be a non empty array")
        if not isinstance(value, list):
            raise ValueError("protocolApplied[0].targetDisease[*].coding must be an array")   
    

# Define the CodeableConcept schema
class ReasonCodeableConceptSchema(Schema):
    coding = fields.List(fields.Nested(ReasonCodingSchema), required=False, error_messages={'invalid':'reasonCode.coding must be an array'})    
    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) != 1 or value == [{}]:
            raise ValueError("reasonCode.coding array must be an array of length 1")
        if not isinstance(value, list):
            raise ValueError("reasonCode.coding must be an array")

class ProtocolAppliedSchema(Schema):
    targetDisease = fields.List(fields.Nested(ProtocolCodeableConceptSchema(field_name= 'protocolApplied')), required=True,error_messages={"required": "protocolApplied[0].targetDisease[0].coding[?(@.system=='http://snomed.info/sct')].code is a mandatory field"})
    doseNumberPositiveInt = fields.Int(required=False, allow_none=True, validate=lambda n: 0 <= n <= 9)
    doseNumberString = fields.Str(required=False, validate=validate.Length(min=1))

    @validates_schema
    def validate_dose_number(self, data, **kwargs):
        if not data.get('doseNumberPositiveInt') and not data.get('doseNumberString'):
            raise ValueError('Either doseNumberPositiveInt or doseNumberString must be present.')
        if data.get('doseNumberPositiveInt') and data.get('doseNumberString'):
            raise ValueError('Only one of doseNumberPositiveInt or doseNumberString should be present.')
    @validates('targetDisease')
    def validate_target_length(self, value):
        if len(value) == 0 or value == [{}]:
            raise ValueError("Every element of protocolApplied[0].targetDisease must have 'coding' property")
        if not isinstance(value, list):
            raise ValueError("protocolApplied[0].targetDiseas must be an array")
        
class ExtensionCodingSchema(Schema):
    system = fields.Str(required=True, error_messages={"required": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')] is a mandatory field", "invalid": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')] must be a string"})
    code = fields.Str(required=True, error_messages={"required": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code is a mandatory field", "invalid": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code must be a string"})
    display = fields.Str(required=False, error_messages={"invalid": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display must be a string"})
    
    @validates('system')
    def validate_extension_length(self, value):
        if len(value) == 0:
            raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')] must be a non-empty string")
        if value != "http://snomed.info/sct":
            raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')] must be unique")

    @validates('code') 
    def validate_code_length(self, value):
        if len(value) == 0:
                raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code must be a non-empty string")
            
    @validates('display')
    def validate_display_length(self, value):
        if len(value) == 0:
                raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct').display must be a non-empty string")        

class ExtensionCodeableConceptSchema(Schema):
    coding = fields.List(fields.Nested(ExtensionCodingSchema), required=True, error_messages={"required":"extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding is a mandatory field ", "invalid": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding must be an array"})
    
    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        super().__init__(*args, **kwargs)

    @validates('coding')
    def validate_extension_length(self, value):
        if len(value) != 1:
            if self.field_name == 'extension':
                raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding array must have exactly one item.")

class ExtensionSchema(Schema):
    url = fields.Str(required=True, error_messages={"required": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')] is a mandatory field", "invalid": "extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')] must be a string"})
    valueCodeableConcept = fields.Nested(ExtensionCodeableConceptSchema(field_name= 'extension'), required=True,error_messages={"required":"extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept is a mandatory field "})

    @validates('url')
    def validate_extension_length(self, value):
        if len(value) == 0:
            raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')] must be a non-empty string")
        if value != "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure":
            raise ValueError("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')] must be unique")

class PatientSchema(Schema):
    reference = fields.Str(required=True, error_messages={'required': 'patient.reference must be a single reference to a contained Patient resource', 'invalid': 'patient.reference must be a string'}) 
    @validates('reference')
    def validate_patient_reference_length(self, value):
        if len(value) == 0:
            raise ValueError("patient.reference must be a single reference to a contained Patient resource")

class ManufacturerSchema(Schema):
    display = fields.Str(required=False, error_messages={'invalid': 'manufacturer.display must be an string'})
    @validates('display')
    def validate_manufacture_display_length(self, value):
        if len(value) == 0:
            raise ValueError("manufacturer.display must be a non-empty string")

def validate_four_decimal_places(value):
    if not re.match(r'^\d+(\.\d{1,4})?$', str(value)):
        raise ValueError('doseQuantity.value must be a number with a maximum of 4 decimal places')    
    if isinstance(value, str):
        raise ValueError('doseQuantity.value must be a number')    

class DoseQuantitySchema(Schema):
    value = fields.Float(required=False, error_messages={"invalid": "doseQuantity.value must be a number"})
    unit = fields.Str(required=False,error_messages={"invalid": "doseQuantity.unit must be a string"})
    system = fields.Str(required=False,error_messages={"invalid": "doseQuantity.system must be a string"})
    code = fields.Str(required=False,error_messages={"invalid": "doseQuantity.code must be a string"})   
    
    @validates('value')
    def validate_value(self, value):
        if isinstance(value, str):
            raise ValueError("doseQuantity.value must be a number")
        validate_four_decimal_places(value)
    
    @validates('unit')
    def validate_unit_length(self, value):
        if len(value) == 0:
            raise ValueError("doseQuantity.unit must be a non-empty string") 
    
    @validates('code')
    def validate_code_length(self, value):
        if len(value) == 0:
            raise ValueError("doseQuantity.code must be a non-empty string")       


class LocationIdentifierSchema(Schema):
    value = fields.Str(required=True, error_messages={"required": "location.identifier.value is a mandatory field", "invalid": "location.identifier.value must be a string"})
    system = fields.Str(required=True, error_messages={"required": "location.identifier.system is a mandatory field", "invalid": "location.identifier.system must be a string"})


    @validates('system')
    def validate_system_length(self, value):
        if len(value) == 0:
            raise ValueError("location.identifier.system must be a non-empty string") 
        if value not in ["https://fhir.nhs.uk/Id/ods-organization-code", "https://fhir.hl7.org.uk/Id/urn-school-number"]:
            raise ValueError("location.identifier.system must be unique'") 
   
    @validates('value')
    def validate_location_length(self, value):
        if len(value) == 0:
            raise ValueError("location.identifier.value must be a non-empty string")
        
class LocationSchema(Schema):
    type = fields.Str(required=True,error_messages={"required": "location.type is a mandatory field", "invalid": "location.type must be a string"})
    identifier = fields.Nested(LocationIdentifierSchema, required=True, error_messages={"required": "location.identifier is a mandatory field  ; location.identifier.system is a mandatory field ; location.identifier.value is a mandatory field"})
    
    @validates('type')
    def validate_type_length(self, value):
        if len(value) == 0:
            raise ValueError("location.type must be a non-empty string") 
        if value != "Location":
            raise ValueError("location.type must be equal to 'Location'") 

class ActorWithoutTypeSchema(Schema):
    reference = fields.Str(required=True,error_messages={"required":"contained Practitioner ID must be referenced by performer.actor.reference", "invalid": "performer.actor.reference must be a string"})
    @validates('reference')
    def validate_reference_length(self, value):
        if len(value) == 0:
            raise ValueError("contained Practitioner ID must be referenced by performer.actor.reference")

    
class ActorIdentifierSchema(Schema):
    system = fields.String(required=True, error_messages={"required": "performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field", "invalid": "performer[?(@.actor.type=='Organization')].actor.identifier.system must be a string"})
    value = fields.String(required=True, validate=validate_identifier,error_messages={"required": "performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field", "invalid": "performer[?(@.actor.type=='Organization')].actor.identifier.value must be string"})
    

    @validates('system')
    def validate_system_length(self, value):
        if len(value) == 0:
            raise ValueError("performer[?(@.actor.type=='Organization')].actor.identifier.system must be a non-empty string")
    
    @validates('value')
    def validate_actor_value_length(self, value):
        if len(value) == 0:
            raise ValueError("performer[?(@.actor.type=='Organization')].actor.identifier.value must be a non-empty string") 
           
class ActorWithTypeSchema(Schema):
    type = fields.Str(required=True, error_messages= {"invalid": "performer[?(@.actor.type=='Organization')] must be a string"} )
    identifier = fields.Nested(ActorIdentifierSchema, required=True, error_messages={"required":"performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field;performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field"})

    @validates('type')
    def validate_type_length(self, value):
        if value != "Organization" or value == 0:
            raise ValueError("performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field; performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field")

class PerformerItemSchema(Schema):
    actor = fields.Nested(ActorWithoutTypeSchema, required=True,error_messages={"required":  "contained Practitioner ID must be referenced by performer.actor.reference"})
    
    @validates('actor')
    def validate_reference_length(self, value):
        if "reference" not in value:
            raise ValueError("contained Practitioner ID must be referenced by performer.actor.reference")

class PerformerItemWithTypeSchema(Schema):
    actor = fields.Nested(ActorWithTypeSchema, required=True,error_messages={"required":"performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field; performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field"})
  
class ImmunizationSchema(Schema):
    resourceType = fields.Str(required=True, validate = [validate_resource_type])
    contained = fields.List(fields.Dict(), required=True)
    extension = fields.List(fields.Nested(ExtensionSchema), required=True, error_messages={'required': 'extension is a mandatory field', "invalid": "extension must be an array"})
    identifier = fields.List(fields.Nested(MainIdentifierSchema), required=True, error_messages={'required': 'identifier[0].value is a mandatory field; identifier[0].system is a mandatory field','invalid': 'identifier must be an array'})
    status = fields.Str(required=True, error_messages={'required': 'status is a mandatory field','invalid':'status must be a string'})
    vaccineCode = fields.Nested(vaccineCodeableConceptSchema(field_name='vaccineCode'), required=False)
    patient = fields.Nested(PatientSchema, required=True,error_messages={'required': 'patient.reference must be a single reference to a contained Patient resource'})
    occurrenceDateTime = fields.Str(required=True,error_messages={"required": "occurrenceDateTime  is a mandatory field", 'invalid': 'occurrenceDateTime must be a string in the format \"YYYY-MM-DDThh:mm:ss+zz:zz\" or \"YYYY-MM-DDThh:mm:ss-zz:zz\" (i.e date and time, including timezone offset in hours and minutes). Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).'})
    recorded = fields.Str(required=True, error_messages = {"required":" recorded is a mandatory field",'invalid':'recorded must be a string in the format \"YYYY-MM-DDThh:mm:ss+zz:zz\" or \"YYYY-MM-DDThh:mm:ss-zz:zz\" (i.e date and time, including timezone offset in hours and minutes). Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).'})
    primarySource = StrictBoolean(required=True,error_messages={"required":" primarySource is a mandatory field"})
    manufacturer = fields.Nested(ManufacturerSchema, required=False)
    location = fields.Nested(LocationSchema, required=True, error_messages={'required': 'location is mandatory field'})
    lotNumber = fields.Str(required=False,error_messages={'invalid':'lotNumber must be a string'})
    expirationDate = Strictdate(required=False,error_messages={'invalid':'expirationDate must be a string'})
    site = fields.Nested(siteCodeableConceptSchema(field_name='site'), required=False)
    route = fields.Nested(routeCodeableConceptSchema(field_name='route'), required=False)
    doseQuantity = fields.Nested(DoseQuantitySchema, required=False)
    performer = fields.List(fields.Dict(), required=True)
    reasonCode = fields.List(fields.Nested(ReasonCodeableConceptSchema), required=False)
    protocolApplied = fields.List(fields.Nested(ProtocolAppliedSchema), required=True,error_messages={'invalid': 'protocolApplied must be an array'})
    
    def validate_single_item(self, field_name, value):
        if len(value) != 1 or value == [{}]:
            raise ValueError(f"{field_name} must be an array of length 1")

    @validates('extension')
    def validate_extension(self, value):
        self.validate_single_item('extension', value)

    @validates('identifier')
    def validate_identifier_check(self, value):
        self.validate_single_item('identifier', value)

    @validates('protocolApplied')
    def validate_protocolApplied(self, value):
        self.validate_single_item('protocolApplied', value) 

    @validates('reasonCode')
    def validate_reasoncode(self, value):
        self.validate_single_item('reasonCode', value)  

    @validates('performer')
    def validate_performer_code(self, value):
        type_organization_present = any(
            performer.get("actor", {}).get("type") == "Organization"
            for performer in value
        )
        if len(value) != 2 and type_organization_present is False :
            raise ValueError("performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field; performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field")   
    

    @validates('status')
    def validate_gender_length(self, value):
        if len(value) == 0:
            raise ValueError("status must be a non-empty string")
        if value not in ["completed"]:
            raise ValueError("status must be equal to completed")    
    @validates('occurrenceDateTime')
    def validate_occurance_length(self, value):
        if len(value) == 0:
            raise ValueError("occurrenceDateTime must be a string in the format \"YYYY-MM-DDThh:mm:ss+zz:zz\" or \"YYYY-MM-DDThh:mm:ss-zz:zz\" (i.e date and time, including timezone offset in hours and minutes). Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).")
        
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[\+\-]\d{2}:\d{2}$'
        is_correct_format = re.match(pattern, value) is not None
        if not is_correct_format:
            raise ValueError("occurrenceDateTime must be a string in the format \"YYYY-MM-DDThh:mm:ss+zz:zz\" or \"YYYY-MM-DDThh:mm:ss-zz:zz\" (i.e date and time, including timezone offset in hours and minutes). Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).")
        try:
            datetime_str = value[:-6]  # remove the timezone part
            datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f') if '.' in datetime_str else datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            raise ValueError("occurrenceDateTime must be a valid datetime")
        
    @validates('recorded')
    def validate_recorded_length(self, value):
        if len(value) == 0:
            raise ValueError("recorded must be a valid date string in the format \"YYYY-MM-DD\"")
        
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[\+\-]\d{2}:\d{2}$'
        is_correct_format = re.match(pattern, value) is not None
        if not is_correct_format:
            raise ValueError("recorded must be a string in the format \"YYYY-MM-DDThh:mm:ss+zz:zz\" or \"YYYY-MM-DDThh:mm:ss-zz:zz\" (i.e date and time, including timezone offset in hours and minutes). Milliseconds are optional after the seconds (e.g. 2021-01-01T00:00:00.000+00:00).")
        try:
            datetime_str = value[:-6]  # remove the timezone part
            datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f') if '.' in datetime_str else datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            raise ValueError("recorded must be a valid datetime")

    
    @validates('primarySource')
    def validate_primary_resource_length(self, value):
        if isinstance(value, str):
            raise ValueError("primarySource must be a boolean")

    @validates('manufacturer')
    def validate_manufactturer_length(self, value):
        if value == {}:
            raise ValueError("manufacturer.display should not be empty")   
        
    @validates('vaccineCode')
    def validate_vaccineCode_length(self, value):
        if value == {}:
            raise ValueError("vaccineCode should not be empty")      

    @validates('lotNumber')
    def validate_lotnumber_length(self, value):
        if len(value) == 0:
            raise ValueError("lotNumber must be a non-empty string")  
        if len(value) > 100:
            raise ValueError("lotNumber must be 100 or fewer characters")  
        
    @validates('doseQuantity')
    def validate_doseQuality_resource_length(self, value):
        if value == {}:
            raise ValueError("doseQuantity should not be empty")      
    

    @validates_schema
    @validates('performer')
    def validate_contained(self, data, performers, **kwargs):
        contained_resources = data.get('contained', [])
        for resource in contained_resources:
            if resource.get('resourceType') != 'Practitioner':
                for performer in performers:
                    actor = performer['actor']
                    if 'reference' in actor:
                        ref = actor['reference']
                        raise ValueError(f"Reference {ref} does not match any Practitioner's id")
            elif resource.get('resourceType') == 'Patient':
                ContainedPatientSchema(field_name="Patient").load(resource)
            else:
                raise ValueError(f"Unsupported resourceType in contained: {resource.get('resourceType')}")     


    @validates_schema
    def validate_contained(self, data, **kwargs):
        contained_resources = data.get('contained', [])
        for resource in contained_resources:
            if resource.get('resourceType') == 'Practitioner':
                PractitionerSchema().load(resource)
            elif resource.get('resourceType') == 'Patient':
                ContainedPatientSchema(field_name="Patient").load(resource)
            else:
                raise ValueError(f"Unsupported resourceType in contained: {resource.get('resourceType')}")   
            
              

    

    @validates('patient')
    def validate_patient_reference(self, value):
        reference = value['reference']
        if not reference.startswith('#'):
            raise ValueError("Reference must start with '#'")
        patient_id = reference[1:]
        contained_resources = self.context.get("contained", [])
        if not any(res['resourceType'] == 'Patient' for res in contained_resources):
            raise ValueError("contained[?(@.resourceType=='Patient')] is mandatory")
        id_present_in_practitioner = any(item["resourceType"] == "Patient" and "id" in item for item in contained_resources)
        if id_present_in_practitioner is False:
            raise ValueError("The contained Patient resource must have an 'id' field")
        if not any(res['resourceType'] == 'Patient' and res['id'] == patient_id for res in contained_resources):
            raise ValueError(f"The reference {reference} does not exist in the contained Patient resource")
        
            
    
    @pre_load
    def differentiate_actors(self, data, **kwargs):
        for i, item in enumerate(data['performer']):
            if 'type' in item['actor']:
                data['performer'][i] = PerformerItemWithTypeSchema().load(item)
            else:
                data['performer'][i] = PerformerItemSchema().load(item)
        return data

    @post_load
    def convert_to_correct_schema(self, data, **kwargs):
        data['performer'] = [PerformerItemWithTypeSchema().dump(item) if 'type' in item['actor'] else PerformerItemSchema().dump(item) for item in data['performer']]
        return data




    @validates('performer')
    def validate_performer(self, performers, **kwargs):


        contained_resources = self.context.get('contained', [])
        # Extract practitioners from contained resources
        practitioners = {item.get('id'): item for item in contained_resources if item["resourceType"] == "Practitioner"}
        # print(f"practitioners{practitioners}")
        
        # Check if there are any practitioners without 'id'
        practitioner_present = any(item["resourceType"] == "Practitioner" for item in contained_resources)
        # print(f"practitioner_present{practitioner_present}")
        practitioners_with_id = any('id' in item for item in contained_resources if item["resourceType"] == "Practitioner")
        # print(f"practitioners_with_id{practitioners_with_id}")
        
        for performer in performers:
            actor = performer['actor']
            ref = actor.get('reference')
            
            if not practitioner_present:
                if ref:
                    raise ValueError(f"Reference {ref} does not exist in the contained Practitioner resource")
                else:
                    # Skip further validation if no practitioners are present and no references are provided
                    continue
            if practitioner_present and practitioners_with_id and ref is None and len(contained_resources) != 2 and "identifier" not in actor:
                raise ValueError("contained Practitioner ID must be referenced by performer.actor.reference")
            
            if ref:
                if not ref.startswith('#'):
                    raise ValueError(f"Reference {ref} does not start with '#'")
                ref_id = ref[1:]  # Remove the '#' to get the id
                if not practitioners_with_id:
                    raise ValueError("The contained Practitioner resource must have an 'id' field") 
                if ref_id not in practitioners:
                    raise ValueError(f"Reference {ref} does not exist in the contained Practitioner resource")
            
        # If practitioners are present, at least one must have an 'id'
        if practitioner_present and not practitioners_with_id:
            raise ValueError("The contained Practitioner resource must have at least one 'id' field")