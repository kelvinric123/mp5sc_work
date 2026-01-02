#!/bin/bash
# ===========================================
# Vital Signs Log Cleanup Script
# ===========================================
# This script cleans up old logs based on the LOG_RETENTION_DAYS setting
# in the .env file. It should be triggered by the systemd timer.

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env file
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Set default retention days if not configured
RETENTION_DAYS=${LOG_RETENTION_DAYS:-7}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting log cleanup..."
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Retention period: ${RETENTION_DAYS} days"

# Clean up journald logs for the vital-signs service
journalctl --vacuum-time=${RETENTION_DAYS}d --unit=vital-signs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log cleanup completed"
