#!/bin/bash
python3 << 'PYTHON'
import re, subprocess, json
from pathlib import Path

task_file = "/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md"
state_file = "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/notified-completions.json"

MICHAEL_PHONE = "+16023771595"
CINDY_PHONE   = "+16023848405"

def imessage(phone, text):
    # Escape quotes for AppleScript
    safe = text.replace('"', "'")
    script = f'''tell application "Messages"
  set s to 1st service whose service type = iMessage
  set b to buddy "{phone}" of s
  send "{safe}" to b
end tell'''
    subprocess.run(["osascript", "-e", script])

# Load already-notified items to prevent spam
state_path = Path(state_file)
try:
    notified = set(json.loads(state_path.read_text())) if state_path.exists() else set()
except:
    notified = set()

with open(task_file, 'r') as f:
    lines = f.readlines()

completed      = []
new_titles     = []
remaining      = []
i = 0

while i < len(lines):
    line = lines[i]
    if re.match(r'^\s*- \[x\]', line, re.IGNORECASE):
        block = [line]
        # Clean title for notification
        title = re.sub(r'^\s*- \[x\]\s*', '', line, flags=re.I).strip()
        title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
        title = re.sub(r'\s*#\w[\w-]*', '', title).strip()
        title = re.sub(r'^[$💌🔥⚡🎯🚗]\s*', '', title).strip()
        title = title[:80]  # cap length
        # Grab indented children
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            if re.match(r'^- \[', next_line) or re.match(r'^##', next_line) or next_line.strip() == '':
                break
            if next_line.startswith(' ') or next_line.startswith('\t'):
                i += 1
                block.append(lines[i])
            else:
                break
        completed.extend(block)
        # Only notify for items we haven't already notified about
        if title and title not in notified:
            new_titles.append(title)
            notified.add(title)
    else:
        remaining.append(line)
    i += 1

if not completed:
    print("No newly checked items found.")
    exit()

# Write updated vault
completed_block = "\n## ✅ Completed\n" + "".join(completed)
content = "".join(remaining)
if "## ✅ Completed" in content:
    content = re.sub(r'(## ✅ Completed\n)', r'\1' + "".join(completed), content)
else:
    content += completed_block

with open(task_file, 'w') as f:
    f.write(content)

count = len(completed)
print(f"Moved {count} completed item(s).")

# Save updated notified state
state_path.write_text(json.dumps(list(notified)))

# Send iMessage only for NEW completions
if new_titles:
    n = len(new_titles)
    if n == 1:
        body = f"✅ Michael completed: {new_titles[0]}"
    else:
        items = "\n• ".join(new_titles[:5])
        body = f"✅ Michael completed {n} items:\n• {items}"

    imessage(MICHAEL_PHONE, body)
    imessage(CINDY_PHONE,   body)
    print(f"   📱 Notified both: {body[:80]}...")
else:
    print("   Already notified about these items — skipping.")
PYTHON
