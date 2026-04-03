#!/bin/bash
echo "👀 Watching Obsidian + Honey list (polling every 5s)..."

TASK_FILE="/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md"
HONEY_FILE="/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/Honey To Do List.md"
LIFELEDGER="/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger"
HONEY_STATE="$LIFELEDGER/honey-done-state.txt"

MICHAEL_PHONE="+16023771595"
CINDY_PHONE="+16023848405"

LAST_MOD_VAULT=$(stat -f "%m" "$TASK_FILE")
LAST_MOD_HONEY=$(stat -f "%m" "$HONEY_FILE")
CHANGED_AT_VAULT=""
CHANGED_AT_HONEY=""

imessage() {
    local phone="$1"
    local text="${2//\"/\'}"  # replace double quotes with single to avoid AppleScript issues
    osascript << OSASCRIPT
tell application "Messages"
  set s to 1st service whose service type = iMessage
  set b to buddy "$phone" of s
  send "$text" to b
end tell
OSASCRIPT
}

# Initialize honey done state if it doesn't exist
if [ ! -f "$HONEY_STATE" ]; then
    touch "$HONEY_STATE"
fi

while true; do

    # ── WATCH YOUR VAULT ──────────────────────────────────────────────────────
    CURRENT_MOD_VAULT=$(stat -f "%m" "$TASK_FILE")
    if [ "$CURRENT_MOD_VAULT" != "$LAST_MOD_VAULT" ]; then
        CHANGED_AT_VAULT=$(date +%s)
        LAST_MOD_VAULT=$CURRENT_MOD_VAULT
    fi

    if [ -n "$CHANGED_AT_VAULT" ]; then
        NOW=$(date +%s)
        DIFF=$((NOW - CHANGED_AT_VAULT))
        if [ "$DIFF" -ge 5 ]; then
            CHECKED=$(grep -c "\- \[x\]" "$TASK_FILE" 2>/dev/null | xargs)
            DROP=$(awk '/## 📥 Drop List/{f=1;next} /^## /{f=0} f && /- \[ \] .+/{print}' "$TASK_FILE" | wc -l | xargs)

            if [ "$CHECKED" -gt "0" ] 2>/dev/null; then
                echo "✅ $(date +%H:%M:%S) — $CHECKED completed item(s), moving..."
                bash "$LIFELEDGER/obsidian-maintenance.sh"
            fi

            if [ "$DROP" -gt "0" ] 2>/dev/null; then
                echo "📥 $(date +%H:%M:%S) — $DROP Drop List item(s), sorting..."
                bash "$LIFELEDGER/sort-drop-list.sh"
            fi

            bash "$LIFELEDGER/vault-backup.sh"
            CHANGED_AT_VAULT=""
        fi
    fi

    # ── WATCH HONEY LIST FOR CINDY'S COMPLETIONS ─────────────────────────────
    CURRENT_MOD_HONEY=$(stat -f "%m" "$HONEY_FILE")
    if [ "$CURRENT_MOD_HONEY" != "$LAST_MOD_HONEY" ]; then
        CHANGED_AT_HONEY=$(date +%s)
        LAST_MOD_HONEY=$CURRENT_MOD_HONEY
    fi

    if [ -n "$CHANGED_AT_HONEY" ]; then
        NOW=$(date +%s)
        DIFF=$((NOW - CHANGED_AT_HONEY))
        if [ "$DIFF" -ge 5 ]; then

            # Find completed [x] items not yet notified
            python3 - << PYTHON
import re, subprocess
from pathlib import Path

honey_file  = "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/Honey To Do List.md"
state_file  = "$HONEY_STATE"
michael     = "$MICHAEL_PHONE"
cindy       = "$CINDY_PHONE"

# Load already-notified titles
try:
    already = set(Path(state_file).read_text().splitlines())
except:
    already = set()

with open(honey_file, 'r') as f:
    lines = f.readlines()

new_done  = []
remaining = []

for line in lines:
    if re.match(r'^\s*- \[x\]', line, re.I):
        title = re.sub(r'^\s*- \[x\]\s*', '', line, flags=re.I).strip()
        title = re.sub(r'\*\*(.+?)\*\*', r'\1', title).strip()
        if title and title not in already:
            new_done.append(title)
            already.add(title)
        # Remove completed line from file
    else:
        remaining.append(line)

if not new_done:
    exit()

# Write cleaned honey list
with open(honey_file, 'w') as f:
    f.writelines(remaining)

# Save updated state
Path(state_file).write_text('\n'.join(already))

# Build message
n = len(new_done)
if n == 1:
    msg = f"💌 Cindy completed: {new_done[0]}"
else:
    items = '\n• '.join(new_done[:5])
    msg = f"💌 Cindy completed {n} items:\n• {items}"

safe_msg = msg.replace('"', "'")

def send(phone, text):
    script = f'''tell application "Messages"
  set s to 1st service whose service type = iMessage
  set b to buddy "{phone}" of s
  send "{text}" to b
end tell'''
    subprocess.run(["osascript", "-e", script])

send(michael, safe_msg)
send(cindy,   safe_msg)
print(f"   📱 Notified both — {msg[:80]}")
PYTHON

            CHANGED_AT_HONEY=""
        fi
    fi

    sleep 5
done
