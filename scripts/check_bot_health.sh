#!/bin/bash
# Health check script for Benfica Discord Bot
# Usage: ./scripts/check_bot_health.sh
# Exit codes: 0 = healthy, 1 = unhealthy, 2 = error

set -e

HEALTH_FILE="bot_health.txt"
MAX_AGE_SECONDS=180  # 3 minutes (allows for 2 missed updates)

# Check if health file exists
if [ ! -f "$HEALTH_FILE" ]; then
    echo "ERROR: Health check file not found: $HEALTH_FILE"
    echo "Bot may not be running or health check not initialized."
    exit 2
fi

# Read timestamp from health file
TIMESTAMP=$(cat "$HEALTH_FILE")

# Convert timestamp to epoch seconds
HEALTH_TIME=$(date -d "$TIMESTAMP" +%s 2>/dev/null || echo 0)
CURRENT_TIME=$(date +%s)

# Calculate age
AGE=$((CURRENT_TIME - HEALTH_TIME))

if [ $AGE -gt $MAX_AGE_SECONDS ]; then
    echo "UNHEALTHY: Bot health check is stale (${AGE}s old, max ${MAX_AGE_SECONDS}s)"
    echo "Last update: $TIMESTAMP"
    exit 1
else
    echo "HEALTHY: Bot is running (last update ${AGE}s ago)"
    echo "Last update: $TIMESTAMP"
    exit 0
fi
