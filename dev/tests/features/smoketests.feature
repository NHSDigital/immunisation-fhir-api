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
		# And The response text should be <response_text>
		Examples:
			| nhsNumber | to_date    | status_code | response_text |
			| 675476587 | 9999-01-01 | 200         | empty         |
			| 675476587 | 9999-01-01 | 200         | empty         |
