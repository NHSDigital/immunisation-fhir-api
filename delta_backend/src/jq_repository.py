SNOMED_SYSTEM_CODE = "http://snomed.info/sct"
EXTENSION_URL  = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
CODING_EXTENSION_URL = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay"

DOSE_UNIT_CODE_QUERY = f'if .doseQuantity.system == "{SNOMED_SYSTEM_CODE}" then .doseQuantity.code else "" end'
DOSE_UNIT_TERM_QUERY = f'.doseQuantity.unit // ""'

VACCINATION_PROCEDURE_TERM_QUERY = f"""
(
  .extension[]?
  | select(.url == "{EXTENSION_URL}")
  | .valueCodeableConcept
) as $valueCodeableConcept
| if $valueCodeableConcept.text? then
    $valueCodeableConcept.text
  else (
    $valueCodeableConcept.coding
    | map(select(.system == "{SNOMED_SYSTEM_CODE}"))
    | first
  ) as $coding
  | (
      $coding.extension[]?
      | select(.url == "{CODING_EXTENSION_URL}")
      | .valueString
    )
    // $coding.display
    // ""
end
"""

# Could be reused (Term search)
VACCINATION_PRODUCT_TERM_QUERY = f'''
if .vaccineCode? and .vaccineCode.text? then
  .vaccineCode.text
else (
  .vaccineCode.coding
  | map(select(.system == "{SNOMED_SYSTEM_CODE}"))
  | first
) as $coding
| (
    $coding.extension[]?
    | select(.url == "{CODING_EXTENSION_URL}")
    | .valueString
  )
  // $coding.display
  // ""
end
'''

# Could be reused (Term search)
SITE_OF_VACCINATION_TERM_QUERY = f'''
if .site? and .site.text? then
  .site.text
else (
  .site.coding
  | map(select(.system == "{SNOMED_SYSTEM_CODE}"))
  | first
) as $coding
| (
    $coding.extension[]?
    | select(.url == "{CODING_EXTENSION_URL}")
    | .valueString
  )
  // $coding.display
  // ""
end
'''

# Could be reused (Term search)
ROUTE_OF_VACCINATION_TERM_QUERY = f'''
if .route? and .route.text? then
  .route.text
else (
  .route.coding
  | map(select(.system == "{SNOMED_SYSTEM_CODE}"))
  | first
) as $coding
| (
    $coding.extension[]?
    | select(.url == "{CODING_EXTENSION_URL}")
    | .valueString
  )
  // $coding.display
  // ""
end
'''
