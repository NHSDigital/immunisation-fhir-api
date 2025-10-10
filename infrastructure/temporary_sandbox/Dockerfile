FROM python:3.9-slim
 
# Install Poetry
RUN pip install poetry && groupadd -r appgroup && useradd -r -g appgroup appuser
 
# Set the working directory
WORKDIR /sandbox
 
# Copy the project configuration and install dependencies
COPY pyproject.toml .
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi 
 
# Copy the application code and set ownership to the non-root user
COPY . /sandbox
RUN chown -R appuser:appgroup /sandbox
 
# Switch to the non-root user
USER appuser
 
# Expose the application port
EXPOSE 9000
 
# Command to run the application
CMD ["uvicorn", "fhir_api:app", "--reload", "--host", "0.0.0.0", "--port", "9000", "--log-level", "warning"]