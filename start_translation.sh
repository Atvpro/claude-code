#!/bin/bash
# Startar översättningen utan tmux-beroende.
# Processen överlever terminalsessioner och tmux-krascher.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="$SCRIPT_DIR/translation.log"
PIDFILE="$SCRIPT_DIR/translation.pid"

# Kolla om redan igång
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Processen körs redan (PID $OLD_PID)"
        exit 0
    fi
fi

echo "Startar översättning med nohup..."
nohup bash "$SCRIPT_DIR/run_translation.sh" >> "$LOGFILE" 2>&1 &
PID=$!
echo $PID > "$PIDFILE"
echo "Startad med PID $PID (se translation.log för progress)"
