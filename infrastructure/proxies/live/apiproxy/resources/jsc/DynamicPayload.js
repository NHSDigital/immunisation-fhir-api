// Parse the response content
var responseContent = context.getVariable("response.content");
var response = JSON.parse(responseContent);

// Set debug message
context.setVariable("debugMessage", "Executing DynamicPayload.js. Parsed Response: " + JSON.stringify(response));

var diagnosticsMessage = "";

// Check response status code
if (response.issue[0].code === "invalid_resource") {
    diagnosticsMessage = "Submitted resource is not valid.";
} else if (response.issue[0].code === "internal_server_error") {
    diagnosticsMessage = "Unexpected internal server error.";
}
// Build dynamic payload
var dynamicPayload = {
    "resourceType": "OperationOutcome",
    // Replace "id" with the correct property from the response
    "id": response.id,
    "meta": {
        "profile": [
            "https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"
        ]
    },
    "issue": [
        {
            "severity": "error",
            // Replace "code" and "diagnostics" with correct properties
            "code": response.issue[0].code,
            "details": {
                "coding": [
                    {
                        "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                        "code": response.issue[0].code
                    }
                ]
            },
            "diagnostics": diagnosticsMessage
        }
    ]
};

// Set the dynamic payload as a variable
context.setVariable("Javascript_dynamic_response", JSON.stringify(dynamicPayload));
