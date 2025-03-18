# Use the official Grafana image
FROM grafana/grafana:latest

# Install Python
USER root
RUN echo "Installing Python..." \
    && apk add --no-cache python3 py3-pip \
    && echo "Python installed successfully."

# Copy provisioning and dashboards
RUN echo "Copying provisioning files..."
COPY ./provisioning /etc/grafana/provisioning
RUN echo "Provisioning files copied."

RUN echo "Copying dashboard files..."
COPY ./dashboards /var/lib/grafana/dashboards
RUN echo "Dashboard files copied."

# Create run.sh
RUN echo '#!/bin/sh\nexec grafana-server' > /run.sh
RUN chmod +x /run.sh

# Expose Grafana port
EXPOSE 3000

# Switch to the non-root user provided by the base image
USER grafana

CMD ["grafana-server", "--homepath=/usr/share/grafana"]