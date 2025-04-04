#!/usr/bin/env bash

while true; do
    for file in $(find /agent/_work -user root); do
        sudo chown agent:agent "${file}"
    done
    sleep 10
done