#!/usr/bin/env bash

# needed because apt background services are sometimes running and that prevents installing packages
# https://codeinthehole.com/tips/avoiding-package-lockout-in-ubuntu-1804/

set -e

function killService() {
    service=$1
    if (sudo systemctl is-enabled -q ${service})
    then
        echo stopping ${service}

        if (sudo systemctl is-active -q ${service})
        then
            sudo systemctl stop ${service}
            sudo systemctl kill --kill-who=all ${service}
    #        sudo systemctl kill --kill-who=all -s SIGKILL ${service}

            # wait until the status of the service is either exited or killed.
            while (sudo systemctl is-active -q ${service})
            do
                echo waiting for stop ..
                sleep 10
            done
        fi

        sudo systemctl mask ${service}
    else
        echo service not enabled ${service}
    fi
}

function disableTimer() {
    service=$1

    if (sudo systemctl status "${service}" > /dev/null ); then
        echo disabling ${service}
        sudo systemctl disable ${service}
    else
        echo service not found ${service}
    fi
}

function disableTimers() {
    disableTimer apt-daily.timer
    disableTimer apt-daily-upgrade.timer
}

function killServices() {
    killService unattended-upgrades.service
    killService apt-daily.service
    killService apt-daily-upgrade.service
}

disableTimers
killServices
sudo killall -9 apt apt-get | true
sudo rm -f /var/lib/apt/lists/lock | true
sudo rm -f /var/cache/apt/archives/lock | true
sudo rm -f /var/lib/dpkg/lock | true
sudo dpkg --configure -a