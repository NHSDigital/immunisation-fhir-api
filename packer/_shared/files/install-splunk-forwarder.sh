#!/usr/bin/env bash

set -e

forwarder_version="${1}"
forwarder_build="${2}"

wget -O /tmp/splunkforwarder.tgz "https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=linux&version=${forwarder_version}&product=universalforwarder&filename=splunkforwarder-${forwarder_version}-${forwarder_build}-Linux-x86_64.tgz&wget=true"

sudo tar xvzf /tmp/splunkforwarder.tgz -C /opt

sudo groupadd splunk

sudo useradd -g splunk splunk

export SPLUNK_HOME=/opt/splunkforwarder

echo SPLUNK_HOME=/opt/splunkforwarder | sudo tee -a /etc/environment

splunk_admin_password=$(openssl rand -base64 14)

sudo bash -c "cat > /opt/splunkforwarder/etc/system/local/user-seed.conf" <<EOL
[user_info]
USERNAME = admin
PASSWORD = ${splunk_admin_password}
EOL


sudo chown -R splunk:splunk /opt/splunkforwarder

sudo /opt/splunkforwarder/bin/splunk enable boot-start --accept-license --answer-yes

sudo mv /tmp/files/shared/update-splunk-forwarder-conf /usr/sbin
sudo chmod +x /usr/sbin/update-splunk-forwarder-conf
sudo mv /tmp/files/shared/update-splunk-forwarder-conf.service /lib/systemd/system
sudo chown root:root /lib/systemd/system/update-splunk-forwarder-conf.service
sudo systemctl daemon-reload
#sudo systemctl start update-splunk-forwarder-conf
#sudo systemctl enable update-splunk-forwarder-conf
#sudo systemctl restart update-dsp-logs-location.service