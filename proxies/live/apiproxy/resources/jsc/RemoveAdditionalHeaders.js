
var allowedHeaders = [
    'Date',
    'Content-Type',
    'Content-Length',
    'Connection',
    'X-Correlation-ID',
    'X-Request-ID',
    'Accept',
    'Strict-Transport-Security'
];

var headers = context.getVariable('request.headers.names');

if(headers) {
    headers.forEach(function(header) {
        if (allowedHeaders.indexOf(header) === -1) {
            context.removeVariable('request.header.' + header);
        }
    });
}

