#!/bin/bash
python3 - << 'PYTHON'
import re
import subprocess
from datetime import datetime

task_file = "/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md"

with open(task_file, 'r') as f:
    lines = f.readlines()

sections = {}
for i, line in enumerate(lines):
    if line.startswith('## '):
        sections[line.strip()] = i

drop_start = None
drop_end = None
for header, idx in sections.items():
    if 'Drop List' in header:
        drop_start = idx
    elif drop_start and idx > drop_start and drop_end is None:
        drop_end = idx

if drop_start is None:
    exit()

# Extract top-level tasks WITH their children as blocks
blocks = []
seen = set()
i = drop_start + 1
end = drop_end or len(lines)

while i < end:
    line = lines[i]
    # Top-level Drop List item (no leading spaces)
    if re.match(r'^- \[ \] .+', line.strip()) and not line.startswith('  ') and not line.startswith('\t'):
        if line.strip() not in seen:
            block = [line]
            seen.add(line.strip())
            # Grab all indented children below it
            while i + 1 < end:
                next_line = lines[i + 1]
                if next_line.startswith(' ') or next_line.startswith('\t'):
                    i += 1
                    block.append(lines[i])
                else:
                    break
            blocks.append((block[0].rstrip(), block, list(range(i - len(block) + 1, i + 1))))
    i += 1

if not blocks:
    exit()

def extract_date(task):
    match = re.search(r'(\d{2}/\d{2}/\d{2,4})', task)
    if match:
        raw = match.group(0)
        for fmt in ['%m/%d/%y', '%m/%d/%Y']:
            try:
                return datetime.strptime(raw, fmt)
            except:
                continue
    return None

def categorize(task):
    t = task.lower()
    today = datetime.now()
    task_date = extract_date(task)
    if task_date:
        days_until = (task_date - today).days
        return 'Time-Sensitive' if days_until <= 3 else 'Scheduled'
    if any(w in t for w in ['urgent','deadline','today','asap','cancel','due','expir','tomorrow']):
        return 'Time-Sensitive'
    if any(w in t for w in ['waiting','follow up','confirm','hear back']):
        return 'Waiting'
    if any(w in t for w in ['buy','get','find','check','research','email','text',
                             'return','pick up','add','mount','install','replace',
                             'clean','dust','drop off','breakdown','break down','grab']):
        return 'Quick'
    if any(w in t for w in ['set up','build','create','plan','fix','negotiate',
                             'review','switch','rollover','apply','audit']):
        return 'Project'
    return 'Someday'

def find_section(keyword):
    for header, idx in sections.items():
        if keyword.lower() in header.lower():
            return header, idx
    return None, None

keyword_map = {
    'Time-Sensitive': 'Time-Sensitive',
    'Scheduled': 'Scheduled',
    'Waiting': 'Waiting',
    'Quick': 'Quick',
    'Project': 'Active',
    'Someday': 'Someday'
}

emoji_map = {
    'Time-Sensitive': 'Time-Sensitive',
    'Scheduled': 'Scheduled',
    'Waiting': 'Waiting On Others',
    'Quick': 'Quick Wins',
    'Project': 'Active Projects',
    'Someday': 'Someday'
}

moved_indices = set()
insertions = {}
notifications = []

for parent_text, block, indices in blocks:
    cat = categorize(parent_text)
    header, target_idx = find_section(keyword_map[cat])
    task_name = re.sub(r'^- \[ \] ', '', parent_text.strip())
    task_name = re.sub(r'#\w+', '', task_name).strip()
    if target_idx is not None:
        if target_idx not in insertions:
            insertions[target_idx] = []
        insertions[target_idx].extend(block)
        for idx in indices:
            moved_indices.add(idx)
        notifications.append((task_name, emoji_map[cat]))
        print(f"Moved block ({len(block)} lines): {task_name} -> {emoji_map[cat]}")
    else:
        print(f"WARNING: No section for {cat}")

new_lines = []
for i, line in enumerate(lines):
    if i in moved_indices:
        continue
    new_lines.append(line)
    if i in insertions:
        for task_line in insertions[i]:
            new_lines.append(task_line if task_line.endswith('\n') else task_line + '\n')

with open(task_file, 'w') as f:
    f.writelines(new_lines)

for task_name, category in notifications:
    script = f'tell application "System Events" to display alert "{task_name}" message "Moved to {category}"'
    subprocess.run(['osascript', '-e', script])
PYTHON
