// extract version from Accept header
function extractVersion() {
    var acceptHeader = context.getVariable("request.header.Accept");
    if (acceptHeader) {
        var versionPattern = /application\/fhir\+json;\s*version=(\d+)/i; // 'i' flag for case-insensitivity
        var validPattern = /^(application\/fhir\+json(;|;\s*version=\d+)?|\*\/\*)$/i; // Valid patterns: with or without version, or */*
        if (validPattern.test(acceptHeader)) {
            var match = acceptHeader.match(versionPattern);
            var version = match ? match[1] : "1"; // Default to version 1 if not provided
            context.setVariable("version", version);
        } else {
            context.setVariable("invalidAcceptHeader", true);
        }
    } else {
        context.setVariable("version", "1"); // Default to version 1 if Accept header is missing
    }
}

extractVersion();
