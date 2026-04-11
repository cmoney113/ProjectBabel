#!/bin/bash

# Execute gtt-portal FIRST
/home/craig/.local/bin/gtt-portal &
PORTAL_PID=$!

# Wait 200ms for the modal to appear
sleep 0.2

# Send the key sequence to auto-accept the modal using stdin syntax with pauses:
# key space,,pause 100,,key tab,,pause 100,,key tab,,pause 100,,key space
echo "key space,,pause 100,,key tab,,pause 100,,key tab,,pause 100,,key space" | /home/craig/.local/bin/wbind

# Start gttd daemon in background SECOND
/home/craig/.local/bin/gttd &
GTTD_PID=$!

# Start gtt daemon in background THIRD
/home/craig/.local/bin/gtt --daemon &
GTT_DAEMON_PID=$!

# Wait for the gtt-portal process to complete (optional)
wait $PORTAL_PID

# Optional: wait for daemons to complete (they usually run indefinitely)
# wait $GTTD_PID
# wait $GTT_DAEMON_PID
