# First Stage
FROM alpine:latest

# Create a non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && apk add --no-cache jq

# Copying OAS spec file into the container
COPY "immunisation-fhir-api.json" ./

# Copying HealthStatus OAS file into the container
COPY "HealthStatusEndpoint.json" ./

# Copying whole specification directory to get inline examples and schemas
COPY ./specification ./specification

# Adding Health status endpoint to main spec file
RUN jq ".paths += $(cat HealthStatusEndpoint.json)" immunisation-fhir-api.json > updated-spec.json

# Second Stage
FROM stoplight/prism:latest

# Create a non-root user in the Prism container
USER root
RUN apk add --no-cache shadow && \
    groupadd -r appgroup && \
    useradd -r -g appgroup appuser

# Inheriting from the previous image and copying updated OAS spec files
COPY --from=0 /specification /usr/src/prism/packages/cli/immunisation-fhir-api/specification
COPY --from=0 /updated-spec.json /usr/src/prism/packages/cli/immunisation-fhir-api/specification/immunisation-fhir-api.json

# Set permissions for the non-root user
RUN chown -R appuser:appgroup /usr/src/prism

# Switch to the non-root user
USER appuser

# Running the Prism mock command with the OAS file
CMD ["mock", "-h", "0.0.0.0", "-p", "9000", "immunisation-fhir-api/specification/immunisation-fhir-api.json"]