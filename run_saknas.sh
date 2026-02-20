#!/bin/bash
cd "$(dirname "$0")"
LOGFILE="translation_saknas.log"
MAX_RESTARTS=100
count=0

while [ $count -lt $MAX_RESTARTS ]; do
    echo "--- START (försök $((count+1))) $(date) ---" >> "$LOGFILE"
    python3 translate_saknas.py >> "$LOGFILE" 2>&1
    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "--- KLAR $(date) ---" >> "$LOGFILE"
        break
    fi

    count=$((count+1))
    echo "--- KRASCH (kod $exit_code), väntar 10s... $(date) ---" >> "$LOGFILE"
    sleep 10
done
