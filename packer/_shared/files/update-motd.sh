#!/usr/bin/env bash

env=${1}
sudo rm -f /etc/update-motd.d/*
cat <<EOF | sudo tee /etc/update-motd.d/00-apm > /dev/null
#!/bin/sh
printf "$(echo -n "apm ${env}" | awk '{print toupper($0)}' | toilet --termwidth --font smmono12 -W | /usr/games/lolcat -f)"
EOF
sudo chmod +x /etc/update-motd.d/00-apm
sudo update-motd > /dev/null
