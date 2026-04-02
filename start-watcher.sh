#!/bin/bash
echo "👀 Watching Obsidian (polling every 5s, 5s quiet period before sorting)..."
TASK_FILE="/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md"
LIFELEDGER="/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger"
LAST_MOD=$(stat -f "%m" "$TASK_FILE")
CHANGED_AT=""

while true; do
    CURRENT_MOD=$(stat -f "%m" "$TASK_FILE")

    if [ "$CURRENT_MOD" != "$LAST_MOD" ]; then
        CHANGED_AT=$(date +%s)
        LAST_MOD=$CURRENT_MOD
    fi

    if [ -n "$CHANGED_AT" ]; then
        NOW=$(date +%s)
        DIFF=$((NOW - CHANGED_AT))

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

            # ── BACKUP after every change ──────────────────────────────
            bash "$LIFELEDGER/vault-backup.sh"

            CHANGED_AT=""
        fi
    fi

    sleep 5
done
