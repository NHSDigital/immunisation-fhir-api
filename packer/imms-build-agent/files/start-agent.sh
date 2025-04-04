#!/usr/bin/env bash

/agent/run.sh >/agent/agent.log 2>&1 &
pid="$!"
echo ${pid}
disown ${pid}

sleep 1
if ! kill -0 ${pid} >/dev/null 2>&1; then
    exit -1
fi