#!/bin/sh
set -e

# Custom initialization logic here
echo "Starting Grafana with custom entrypoint script..."

# Start Grafana
exec grafana-server --homepath=/usr/share/grafana