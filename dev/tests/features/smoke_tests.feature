Feature: SmokeTests

	Background: I am testing the local environment
		Given I am testing the local environment

	Scenario: Immunization Root Check
		When I invoke the root endpoint for the Immunization api
		Then The response status code should be 200
		And The response text should be FHIR API

	Scenario: Immunization Health Check
		When I invoke the health endpoint for the Immunization api
		Then The response status code should be 200
		And The response text should be empty

	Scenario Outline: Immunization Health Check2
		When I get the immunisation endpoint with the parameters nhsNumber=<nhsNumber> to_date=<to_date>
		Then The response status code should be <status_code>
		And The response json should match <response_file>
		Examples:
			| nhsNumber | to_date    | status_code | response_file                   |
			| 67547658  | 9999-01-01 | 200         | immunization_invalid_nhs_number |
			| 23838008  | 9999-01-01 | 200         | immunization_valid_nhs_number   |
