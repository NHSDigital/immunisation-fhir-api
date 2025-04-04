#! /bin/sh

### BEGIN INIT INFO
# Provides:          vsts-agent
# Default-Start:     4 5
# Default-Stop:      0 1 6
# Short-Description: vsts agent service
# Description:       azure devops agent as a service
### END INIT INFO

set -e

# /etc/init.d/rsync: start and stop the rsync daemon
DAEMON=/agent/run.sh
PID_FILE=/var/run/vsts-agent.pid
LOCK_FILE=/var/lock/subsys/vsts-agent
IS_CONFIGURED=/var/run/vsts-agent.configured

test -x $DAEMON || exit 0

. /lib/lsb/init-functions


configure() {
    log_daemon_msg "configuring agent" "vsts-agent"

    if [ -f $IS_CONFIGURED ]; then
        log_daemon_msg "agent already configured" "vsts-agent"
        return 0
    fi

    AZ_POOL="${AZ_POOL-AWS-ECS}"
    AZ_URL="${AZ_URL-https://dev.azure.com/NHSD-APIM}"
    AZ_CI="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_ID --query SecretString --output text)"
    AZ_CS="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_SECRET --query SecretString --output text)"
    AZ_TN="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_TENANT --query SecretString --output text)"
    export AZ_CI="${AZ_CI}"
    export AZ_CS="${AZ_CS}"
    export AZ_TN="${AZ_TN}"
    AZ_TOKEN="$(az-get-token)"

    su - agent -c "/agent/config.sh --unattended --url \"${AZ_URL}\" --auth pat --token \"${AZ_TOKEN}\" --pool \"${AZ_POOL}\" --acceptTeeEula >/agent/agent-config.log 2>&1"

    touch $IS_CONFIGURED
}

remove() {
    log_daemon_msg "removing agent" "vsts-agent"

    if [ ! -f $IS_CONFIGURED ]; then
        log_daemon_msg "agent not configured" "vsts-agent"
        return 0
    fi

    AZ_POOL="${AZ_POOL-AWS-ECS}"
    AZ_URL="${AZ_URL-https://dev.azure.com/NHSD-APIM}"
    AZ_CI="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_ID --query SecretString --output text)"
    AZ_CS="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_SECRET --query SecretString --output text)"
    AZ_TN="$(aws --region eu-west-2 secretsmanager get-secret-value --secret-id AZURE/AGENT_CLIENT_TENANT --query SecretString --output text)"
    export AZ_CI="${AZ_CI}"
    export AZ_CS="${AZ_CS}"
    export AZ_TN="${AZ_TN}"
    AZ_TOKEN="$(az-get-token)"

    su - agent -c "/agent/config.sh remove --unattended --auth pat --token \"${AZ_TOKEN}\" >/agent/agent-config.log 2>&1"

    rm -f $IS_CONFIGURED || true
}


start() {
    log_daemon_msg "starting agent"
    if [ -s $PID_FILE ] && kill -0 $(cat $PID_FILE) >/dev/null 2>&1; then
        log_progress_msg "apparently already running"
        log_end_msg 0
        exit 0
    fi

     if [ -s "$IS_CONFIGURED" ]; then
        [ "$VERBOSE" != no ] && log_warning_msg "not configured, not starting..."
        log_end_msg 1
        exit -1
    fi

    if pid=$(su - agent '/start-agent.sh'); then
        rc=0
        sleep 1
        if ! kill -0 ${pid} >/dev/null 2>&1; then
            log_failure_msg "service failed to start"
            rc=1
        fi
        echo "${pid}" > ${PID_FILE}
    else
        rc=1
    fi
    if [ $rc -eq 0 ]; then
        touch $LOCK_FILE
        log_end_msg 0
    else
        log_end_msg 1
        rm -f $PID_FILE
    fi
}

stop() {
    log_daemon_msg "Stopping agent" "vsts-agent"
    if [ -s $PID_FILE ] && kill -0 $(cat $PID_FILE) >/dev/null 2>&1; then
        RETVAL=0
        if kill $(cat $PID_FILE); then
            log_end_msg 0
        else
            log_end_msg 1
            RETVAL=1
        fi
    fi
    rm -f $PID_FILE
    rm -f $LOCK_FILE
    exit $RETVAL
}

case "$1" in
  start)
    configure
    start
    ;;
  stop)
    remove
    stop
    ;;
  status)
    status_of_proc -p $PID_FILE $DAEMON
    exit $?	# notreached due to set -e
    ;;
  *)
    echo "Usage: /etc/init.d/vsts-agent {start|stop|status}"
    exit 1
esac

exit 0