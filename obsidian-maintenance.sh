#!/bin/bash
python3 << 'PYTHON'
import re

task_file = "/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md"

with open(task_file, 'r') as f:
    lines = f.readlines()

completed = []
remaining = []
i = 0

while i < len(lines):
    line = lines[i]
    if re.match(r'^\s*- \[x\]', line, re.IGNORECASE):
        block = [line]
        # Grab ALL indented lines below (any style: -, •, numbers, plain indent)
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            # Stop if next line is a top-level item or empty section header
            if re.match(r'^- \[', next_line) or re.match(r'^##', next_line) or next_line.strip() == '':
                break
            # If it's indented at all, it belongs to this block
            if next_line.startswith(' ') or next_line.startswith('\t'):
                i += 1
                block.append(lines[i])
            else:
                break
        completed.extend(block)
    else:
        remaining.append(line)
    i += 1

if not completed:
    print("No newly checked items found.")
    exit()

completed_block = "\n## ✅ Completed\n" + "".join(completed)
content = "".join(remaining)

if "## ✅ Completed" in content:
    content = re.sub(r'(## ✅ Completed\n)', r'\1' + "".join(completed), content)
else:
    content += completed_block

with open(task_file, 'w') as f:
    f.write(content)

count = len([c for c in completed if re.match(r'^\s*- \[x\]', c, re.IGNORECASE)])
print(f"Moved {count} completed item(s) with all sub-bullets.")
PYTHON
