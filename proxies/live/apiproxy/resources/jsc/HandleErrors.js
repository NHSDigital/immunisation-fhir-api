function makeResponse(errorObject, statusCode) {
    return {
        content: JSON.stringify(errorObject),
        statusCode: statusCode
    }
}

function handleError(context) {
    // Authorization
    const tokenFaultName = context.getVariable("oauthV2.OauthV2.VerifyAccessToken.fault.name")

    if (tokenFaultName === "keymanagement.service.invalid_access_token") {
        return makeResponse(errorRepository["401UnauthorizedSecurity"], 401)
    }
    if (tokenFaultName === "oauth.v2.InvalidAccessToken") {
        return makeResponse(errorRepository["401UnauthorizedExpired"], 401)
    }
    if (context.getVariable("oauthV2.OauthV2.VerifyAccessToken.failed")) {
        return makeResponse(errorRepository["401UnauthorizedSecurity"], 401)
    }
}

var errorResponse = null;

const validationError = context.getVariable("validation.error")
if (validationError) {
    errorResponse  = makeResponse(errorRepository[validationError.name], validationError.statusCode)
} else {
    errorResponse = handleError(context)
}

context.setVariable("errorContent", errorResponse.content)
context.setVariable("errorStatusCode", errorResponse.statusCode)