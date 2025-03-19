#!/bin/sh
echo "Grafana Docker container startup..."

GRAFANA_SERVER_PATH=$(which grafana-server)
if [ -z "$GRAFANA_SERVER_PATH" ]; then
    echo "grafana-server not found. Exiting."
    exit 1
else
    echo "grafana-server found at $GRAFANA_SERVER_PATH"
fi

echo "Starting Grafana with environment variables:"
env | grep GF_

# Check if Grafana configuration exists
if [ ! -f /etc/grafana/grafana.ini ]; then
    echo "Grafana configuration not found. Exiting."
    exit 1
fi

GF_UPDATE_CHECK=false

# Start Grafana in the foreground
echo "Starting Grafana server..."
exec $GF_PATHS_HOME/bin/grafana-server \
  --homepath=$GF_PATHS_HOME \
  --config=/etc/grafana/grafana.ini \
  --packaging=docker \
  cfg:default.paths.data=/var/lib/grafana \
  cfg:default.paths.logs=/var/log/grafana \
  cfg:default.paths.plugins=/var/lib/grafana/plugins \
  cfg:default.paths.provisioning=/etc/grafana/provisioning