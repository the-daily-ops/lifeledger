#!/bin/bash
# LifeLedger Vault Backup
# Commits the Obsidian vault to a local git repo on every change.
# Called automatically by start-watcher.sh after every vault update.
# Also safe to run manually anytime: bash vault-backup.sh

VAULT_DIR="/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

cd "$VAULT_DIR" || exit 1

# Initialize git repo if it doesn't exist yet
if [ ! -d ".git" ]; then
    git init
    echo ".obsidian/" >> .gitignore
    echo ".DS_Store" >> .gitignore
    echo "*.canvas" >> .gitignore
    echo "*.base" >> .gitignore
    git add .
    git commit -m "Initial vault backup"
    echo "✅ Vault git repo initialized"
fi

# Commit any changes
git add -A
CHANGES=$(git diff --cached --name-only)

if [ -n "$CHANGES" ]; then
    git commit -m "Auto-backup $TIMESTAMP"
    echo "💾 Vault backed up — $TIMESTAMP"
else
    echo "   No vault changes to back up"
fi
