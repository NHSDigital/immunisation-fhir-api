#!/usr/bin/env bash

set -e

if hash aws 2>/dev/null; then
    echo aws cli already installed
    exit 0
fi

PACKAGE_MANAGER=''
if hash apt; then
    PACKAGE_MANAGER='apt'
else
    if hash yum; then
        PACKAGE_MANAGER='yum'
    fi
fi

echo aws cli needs installing

# prefer python 3 install as that's what we mostly use
if hash python3 2>/dev/null; then

    if ! hash pip3 2>/dev/null; then
        sudo ${PACKAGE_MANAGER} install -y python3-pip
    fi

    sudo pip3 install --upgrade pip==18.01 awscli
    exit 0
fi

if hash python 2>/dev/null; then

    if ! hash pip 2>/dev/null; then
        sudo ${PACKAGE_MANAGER} install -y python-pip
    fi

    sudo pip install --upgrade pip==18.01 awscli
    exit 0
fi

echo aws cli not installed / installable
exit 1