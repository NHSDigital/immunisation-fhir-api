#!/usr/bin/env bash

set -e

node_exporter_version="${1}"

wget https://github.com/prometheus/node_exporter/releases/download/v${node_exporter_version}/node_exporter-${node_exporter_version}.linux-amd64.tar.gz -P /tmp
tar -xvf /tmp/node_exporter-${node_exporter_version}.linux-amd64.tar.gz -C /tmp
sudo mv /tmp/node_exporter-${node_exporter_version}.linux-amd64/node_exporter /usr/bin/prometheus-node-exporter
sudo useradd -rs /bin/false prometheus
sudo mv /tmp/files/shared/prometheus/prometheus-node-exporter.conf /etc/default/prometheus-node-exporter
sudo mv /tmp/files/shared/prometheus/prometheus-node-exporter.service /lib/systemd/system/
sudo mkdir -p /var/lib/prometheus/node-exporter
sudo chmod a+w /var/lib/prometheus/node-exporter
sudo chown root:root /usr/bin/prometheus-node-exporter
sudo chown root:root /lib/systemd/system/prometheus-node-exporter.service
sudo chown root:root /etc/default/prometheus-node-exporter
sudo systemctl daemon-reload
sudo systemctl start prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl restart prometheus-node-exporter.service