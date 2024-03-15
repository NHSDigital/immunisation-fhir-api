var responseContent = context.getVariable("response.content");
var response = JSON.parse(responseContent);
var diagnosticsMessage = "";

if (response.issue[0].code === "unprocessable_entity") {
    diagnosticsMessage = "The proposed resource violated applicable FHIR profiles or server business rules."
} else if (response.issue[0].code === "internal_server_error") {
    diagnosticsMessage = "Unexpected internal server error.";
}

var dynamicPayload = {
    "resourceType": "OperationOutcome",
    "id": response.id,
    "meta": {
        "profile": [
            "https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"
        ]
    },
    "issue": [
        {
            "severity": "error",
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

context.setVariable("Javascript_dynamic_response", JSON.stringify(dynamicPayload));
