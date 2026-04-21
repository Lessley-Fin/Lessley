#!/usr/bin/env bash
set -euo pipefail

# Substitute cron schedule env var into the crontab
sed -i "s|SWISH_CRON_PLACEHOLDER|${SWISH_CRON}|" /etc/cron.d/swish
crontab /etc/cron.d/swish

# Ensure data directories exist
mkdir -p "${SWISH_DATA_DIR}" "${DEALS_DATA_DIR}"

# Create log file and make it readable by tail
touch /var/log/swish.log

# Optional immediate run (set SWISH_RUN_ON_START=1 in compose or docker run)
if [ "${SWISH_RUN_ON_START:-0}" = "1" ]; then
    python -m deals swish-all >> /var/log/swish.log 2>&1 &
fi

# Start cron daemon in background
cron

# Tail the log to stdout so `docker logs swish-scanner` shows all output
exec tail -F /var/log/swish.log
