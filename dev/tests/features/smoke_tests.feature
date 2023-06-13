Feature: Smoke Tests

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


