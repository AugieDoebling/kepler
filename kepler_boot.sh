#!/usr/bin/env bash
#
# Starts Kepler at boot. Meant to be run by cron, e.g. in `crontab -e` as the kepler user:
#
#   @reboot /home/kepler/kepler/kepler_boot.sh
#
# Cron gives a bare environment (no PATH beyond /usr/bin:/bin, no terminal, home directory as the
# working directory), so this script sets up everything main.py expects before starting it.
# Its own output and main.py's stdout/stderr go to logs/boot_<date>.log; main.py's log is unchanged.

set -u

# How long to wait for the network and the clock before starting anyway
NETWORK_WAIT_SECONDS=90

KEPLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$KEPLER_DIR" || exit 1

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1
export GIT_TERMINAL_PROMPT=0
# Some audio stacks look for the user's session runtime directory, which cron does not set
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -d "/run/user/$(id -u)" ]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi

mkdir -p logs

# Only one Kepler at a time: two would fight over the serial port, the servos and the displays
exec 9>"logs/.kepler_boot.lock"
if ! flock -n 9; then
    echo "Kepler is already running, not starting another" >&2
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [boot] $*"
}

# The Pi has no battery backed clock, so the date can be wrong until NTP syncs. Waiting for it keeps
# the log file names right and stops TLS to the LLM APIs failing on certificate dates.
wait_for_network_and_clock() {
    local waited=0
    while [ "$waited" -lt "$NETWORK_WAIT_SECONDS" ]; do
        if ip route show default 2>/dev/null | grep -q . \
            && getent hosts github.com >/dev/null 2>&1 \
            && [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ]; then
            log "Network up and clock synced after ${waited}s"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    log "Network or clock still not ready after ${NETWORK_WAIT_SECONDS}s, starting anyway"
    return 1
}

# Decided before the clock is right, so it is renamed below once the date is known
BOOT_LOG="logs/boot_pending.log"
exec >>"$BOOT_LOG" 2>&1
log "Boot script started in $KEPLER_DIR"

if wait_for_network_and_clock; then
    network_ready=1
else
    network_ready=0
fi

DATED_LOG="logs/boot_$(date +%Y-%m-%d).log"
cat "$BOOT_LOG" >>"$DATED_LOG" && rm -f "$BOOT_LOG"
exec >>"$DATED_LOG" 2>&1

# Pull the latest code. Only a fast forward, so local edits on the robot are never merged or lost;
# if it cannot, Kepler starts on the code it already has.
if [ "$network_ready" -eq 1 ]; then
    if timeout 60 git pull --ff-only origin main; then
        log "Code is at $(git rev-parse --short HEAD)"
    else
        log "git pull failed, starting on $(git rev-parse --short HEAD)"
    fi
else
    log "Skipping git pull, no network"
fi

if [ ! -x ".venv/bin/python" ]; then
    log "No virtual environment at $KEPLER_DIR/.venv, cannot start"
    exit 1
fi

# With no terminal, typed input reads end-of-file at once; without speech input the LLM thread
# has nothing to listen to
if ! .venv/bin/python -c 'import json, sys; sys.exit(0 if json.load(open("kepler_config.json")).get("audio_input") else 1)' 2>/dev/null; then
    log "Warning: audio_input is off in kepler_config.json, Kepler cannot hear anything when started from cron"
fi

# exec so main.py gets cron's SIGTERM at shutdown directly and runs its own shut down
log "Starting main.py"
exec .venv/bin/python main.py "$@" </dev/null
