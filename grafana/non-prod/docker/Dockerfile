# Use the official Grafana image
FROM grafana/grafana:latest

# Install Python
USER root
RUN echo "Installing Python..." \
    && apk add --no-cache python3 py3-pip \
    && echo "Python installed successfully."

# set timeout for plugin installation
ENV GF_INSTALL_PLUGINS_TIMEOUT=6000
ENV GF_UPDATE_CHECK=false

# Install Grafana plugins
RUN echo "Installing plugins..." \
    && grafana-cli plugins install grafana-lokiexplore-app \
    && grafana-cli plugins install grafana-pyroscope-app 

# Copy custom grafana.ini configuration file
COPY ./grafana.ini /etc/grafana/grafana.ini

# Copy provisioning and dashboards
RUN echo "=========\n\n\n\Copying provisioning files..."
COPY ./provisioning /etc/grafana/provisioning
RUN echo "Provisioning files copied."

RUN echo "Copying dashboard files..."
COPY ./dashboards /var/lib/grafana/dashboards
RUN echo "Dashboard files copied."

COPY run.sh /run.sh
RUN chmod +x /run.sh

# Expose Grafana port
EXPOSE 3000

# Switch to the non-root user provided by the base image
USER grafana

ENTRYPOINT ["/run.sh"]
