#!/bin/bash
# LifeLedger Dashboard Scheduler — Install Script
# Run this ONCE in Terminal to set up the auto-refresh.
# Usage: bash /Users/coto/Documents/LifeLedger/install-scheduler.sh

PLIST_SRC="/Users/coto/Documents/LifeLedger/com.coto.lifeledger.dashboard.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist"

echo ""
echo "🗂  LifeLedger Dashboard Scheduler"
echo "────────────────────────────────────"

# Copy plist to LaunchAgents
echo "→ Installing plist to LaunchAgents..."
cp "$PLIST_SRC" "$PLIST_DEST"

# Load it into launchd
echo "→ Loading scheduler..."
launchctl load "$PLIST_DEST"

echo ""
echo "✅ Done! Dashboard will now auto-refresh every 30 minutes."
echo ""
echo "   Useful commands:"
echo "   • Check status:  launchctl list | grep lifeledger"
echo "   • Force refresh: python3 /Users/coto/Documents/LifeLedger/generate-dashboard.py"
echo "   • Stop:          launchctl unload ~/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist"
echo "   • Restart:       launchctl load ~/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist"
echo ""
echo "   Logs: /Users/coto/Documents/LifeLedger/dashboard-scheduler.log"
echo ""
