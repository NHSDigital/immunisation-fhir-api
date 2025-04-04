#!/usr/bin/env bash

set -e

sudo apt install -yq chrony
sudo sed -i '1s/^/server 169.254.169.123 prefer iburst\n/' /etc/chrony/chrony.conf
sudo /etc/init.d/chrony restart