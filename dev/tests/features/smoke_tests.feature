Feature: Smoke Tests

	Background: I am testing the local environment
		Given I am testing the local environment

	Scenario: Immunisation Root Check
		When I invoke the root endpoint for the Immunisation api
		Then The response status code should be 200
		And The response text should be FHIR API

	Scenario: Immunisation Health Check
		When I invoke the health endpoint for the Immunisation api
		Then The response status code should be 200
		And The response text should be empty
