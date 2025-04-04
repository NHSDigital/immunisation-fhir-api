#!/usr/bin/env bash

set -e

mkdir ~/.aws
echo '[default]' > ~/.aws/config
echo 'output = json' >> ~/.aws/config
echo 'region = eu-west-2' >> ~/.aws/config
sudo cp -r ~/.aws /root