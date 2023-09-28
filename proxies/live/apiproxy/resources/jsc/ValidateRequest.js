function validEndpoint(context) {
    const path = context.getVariable("proxy.pathsuffix")
    return path.startsWith("/event") ||
        path.startsWith("/_ping") ||
        path.startsWith("/_status")
        // || path.startsWith(etc, etc, etc)
}

function hasRequiredHeaders(context) {
    const headers = context.getVariable("request.headers.names").toArray()

    const hasHeader = (name) => {
        for (var i = 0; i < headers.length; i++) {
            if (String(headers[i]).toLowerCase().trim() === name.toLowerCase().trim()) return true
        }
        return false
    }
    return hasHeader("x-request-id") && hasHeader("x-correlation-id")
}

function validate(context) {
    if (!validEndpoint(context)) {
        return {
            name: "404PageNotFound",
            statusCode: 404

        }
    }
    if (!hasRequiredHeaders(context)) {
        return {
            name: "400InvalidHeaders",
            statusCode: 400

        }
    }

    return null
}

context.setVariable("validation.error", validate(context))