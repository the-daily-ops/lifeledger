#!/usr/bin/env python3
"""
LifeLedger Dashboard Auto-Generator
Reads Obsidian vault + wife's Honey list → writes dashboard.html → publishes to Netlify.
"""

import re, json, subprocess, calendar
from pathlib import Path
from datetime import datetime, date, timedelta

# ── PATHS ──────────────────────────────────────────────────────────────────────
VAULT_FILE  = Path("/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal/01 Daily/2026-02-25.md")
HONEY_FILE  = Path("/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/Honey To Do List.md")
OUTPUT_FILE = Path("/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/dashboard.html")
REPO_DIR    = "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger"
TODAY       = date.today()

# Checkbox items to exclude from wife banner (test entries, supplements, teas etc shown elsewhere)
WIFE_BANNER_EXCLUDE = re.compile(
    r"^(one time|one more time|coq10|prenatal|fish oil|flaxseed|magnesium|"
    r"morning|afternoon|evening|pineapple juice|pomegranate juice|nettle|rosehip|peppermint)$",
    re.I
)

# ── PARSERS ────────────────────────────────────────────────────────────────────
def parse_tasks(text, section_name):
    tasks, in_section = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = section_name in line; continue
        if in_section and re.match(r"^- \[ \]", line):
            title = re.sub(r"^- \[ \] ", "", line).strip()
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
            is_money = "$" in title
            title = re.sub(r"\s+#\w[\w-]*", "", title).replace("$ ","").replace("$","").strip()
            tags = re.findall(r"#(\w[\w-]*)", line)
            tasks.append({
                "title": title, "money": is_money,
                "tags": [t for t in tags if t not in ["p1","p2","wife-priority"]],
                "urgent": any(t in ["p1","wife","family"] for t in tags),
                "wife": "wife" in line.lower() or "💌" in line,
            })
    return tasks

def parse_vault_events(text):
    events, in_section = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = "Dates" in line or "Events" in line; continue
        if in_section and line.startswith("- **"):
            events.append(line.lstrip("- ").strip())
    return events

def parse_honey_events(text):
    events, in_events = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"(April on the Radar|Coming up Soon|Events|This Week)", stripped, re.I):
            in_events = True; continue
        if stripped.startswith("##") and not re.search(r"(radar|soon|event|week)", stripped, re.I):
            in_events = False; continue
        if not in_events or not stripped: continue
        if stripped.startswith("- ") and not stripped.startswith("- [ ]") and not stripped.startswith("- [x]"):
            content = stripped.lstrip("- ").strip().lstrip("*").strip()
            if content and len(content) > 2:
                events.append(content)
        elif re.match(r"^- \[[ x]\]", stripped):
            content = re.sub(r"^- \[[ x]\] ","", stripped).strip()
            content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)
            if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d+/\d+|april|march)", content, re.I):
                events.append("💌 " + content)
    return events

def parse_wife_checkboxes(text):
    """Extract [ ] tasks for wife banner, filtering out supplements/test entries."""
    tasks = []
    for line in text.splitlines():
        if re.match(r"^- \[ \]", line):
            title = re.sub(r"^- \[ \] ","", line).strip()
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
            # Skip test entries and routine supplement/tea items
            clean = re.sub(r"[^\w\s]","", title).strip()
            if WIFE_BANNER_EXCLUDE.match(clean):
                continue
            tasks.append(title)
    return tasks

# ── DATE PARSING ───────────────────────────────────────────────────────────────
def try_parse_date(text):
    year = TODAY.year
    patterns = [
        (r"\b(\d{1,2})/(\d{1,2})\b",
         lambda m: date(year, int(m.group(1)), int(m.group(2)))),
        (r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})",
         lambda m: datetime.strptime(f"{m.group(1)[:3].capitalize()} {m.group(2)} {year}", "%b %d %Y").date()),
        (r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
         lambda m: datetime.strptime(f"{m.group(2)[:3].capitalize()} {m.group(1)} {year}", "%b %d %Y").date()),
        (r"(sat|sun|mon|tue|wed|thu|fri)[a-z]*\s+(\d{1,2})/(\d{1,2})",
         lambda m: date(year, int(m.group(2)), int(m.group(3)))),
        (r"(\d{1,2})/(\d{1,2})\s+(sat|sun|mon|tue|wed|thu|fri)",
         lambda m: date(year, int(m.group(1)), int(m.group(2)))),
        (r"\b(april|may|june|july|august|september|october|november|december|january|february|march)\s+(\d{1,2})",
         lambda m: datetime.strptime(f"{m.group(1)[:3].capitalize()} {m.group(2)} {year}", "%b %d %Y").date()),
    ]
    for pattern, parser in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            try:
                d = parser(m)
                if d < TODAY - timedelta(days=1): d = d.replace(year=year+1)
                return d
            except: pass
    return None

def days_until(d): return (d - TODAY).days if d else 999
def urgency(days):
    if days <= 3:  return "urg"
    if days <= 7:  return "soon"
    if days <= 14: return "upcoming"
    return "future"

def collect_events(vault_events, honey_events):
    all_evs, seen = [], set()
    for raw in vault_events + honey_events:
        key = re.sub(r"[^\w]","", raw.lower())[:30]
        if key in seen: continue
        seen.add(key)
        d     = try_parse_date(raw)
        days  = days_until(d)
        is_wife = raw.startswith("💌") or any(
            w in raw.lower() for w in ["date night","dental","c's","pregnancy","wedding","easter","birthday"])
        # Clean display — strip leading date/day-of-week patterns
        display = re.sub(r"^\d{1,2}/\d{1,2}\s*(sat|sun|mon|tue|wed|thu|fri)[a-z]*\s*","",raw,flags=re.I).strip()
        display = re.sub(r"^(sat|sun|mon|tue|wed|thu|fri)[a-z]*\s+\d{1,2}/\d{1,2}\s*","",display,flags=re.I).strip()
        display = re.sub(r"^\*+|\*+$","",display).strip(" —-·")
        if not display: display = raw
        all_evs.append({
            "raw": raw, "display": display, "date": d,
            "days": days, "is_wife": is_wife, "urgency": urgency(days),
            "date_str": d.strftime("%b %-d") if d else "",
            "countdown": (
                f"{days}d away" if days > 1
                else "tomorrow" if days == 1
                else "TODAY" if days == 0
                else "passed"
            ) if d else "",
        })
    all_evs.sort(key=lambda x: x["days"])
    return all_evs

# ── CALENDAR BUILDER ──────────────────────────────────────────────────────────
def build_calendar_html(events):
    """Build April + May (or current + next month) calendar grids."""
    ev_by_date = {}
    for ev in events:
        if ev["date"]:
            key = (ev["date"].month, ev["date"].day, ev["date"].year)
            ev_by_date.setdefault(key, []).append(ev)

    months_html = []
    # Always show current month + next month
    for offset in range(2):
        m = (TODAY.month - 1 + offset) % 12 + 1
        y = TODAY.year + ((TODAY.month - 1 + offset) // 12)
        month_name = datetime(y, m, 1).strftime("%B %Y")
        cal = calendar.monthcalendar(y, m)

        dow_row = "".join(f'<div class="cdow">{d}</div>' for d in ["Su","Mo","Tu","We","Th","Fr","Sa"])
        cells = []
        for week in cal:
            for day in week:
                if day == 0:
                    cells.append('<div class="ccell cempty"></div>'); continue
                d    = date(y, m, day)
                key  = (m, day, y)
                evs  = ev_by_date.get(key, [])
                cls  = "ccell"
                if d == TODAY:        cls += " ctoday"
                elif d < TODAY:       cls += " cpast"

                # Up to 3 colored dots
                dots = "".join(
                    f'<span class="cdot cdot-{"wife" if e["is_wife"] else e["urgency"]}"></span>'
                    for e in evs[:3]
                )
                # Up to 1 short label
                label = ""
                if evs:
                    e = evs[0]
                    lc = "wife" if e["is_wife"] else e["urgency"]
                    short = e["display"][:14] + ("…" if len(e["display"]) > 14 else "")
                    label = f'<div class="clbl clbl-{lc}">{short}</div>'

                tip = "; ".join(e["display"] for e in evs)
                tip_attr = f' title="{tip}"' if tip else ""
                cells.append(
                    f'<div class="{cls}"{tip_attr}>'
                    f'<span class="cdaynum">{day}</span>'
                    f'<div class="cdots">{dots}</div>'
                    f'{label}'
                    f'</div>'
                )

        months_html.append(
            f'<div class="cal-month">'
            f'<div class="cal-mname">{month_name}</div>'
            f'<div class="cgrid">{dow_row}{"".join(cells)}</div>'
            f'</div>'
        )
    return "\n".join(months_html)

def build_event_cards_html(events):
    cards = []
    for ev in events[:15]:
        u  = ev["urgency"]
        wc = " ev-wife" if ev["is_wife"] else ""
        cards.append(
            f'<div class="evc ev-{u}{wc}">'
            f'<div class="evc-top">'
            f'<span class="evc-date">{ev["date_str"]}</span>'
            f'<span class="evc-cd">{ev["countdown"]}</span>'
            f'</div>'
            f'<div class="evc-title">{ev["display"]}</div>'
            f'</div>'
        )
    return "\n".join(cards)

def tasks_to_js(tasks, col, start_id=100):
    lines = []
    for i, t in enumerate(tasks):
        title = t["title"].replace("'","\\'").replace("`","")
        lines.append(
            f"  {{id:{start_id+i},col:'{col}',title:'{title}',note:'',"
            f"tags:{json.dumps(t.get('tags',[]))},money:{'true' if t.get('money') else 'false'},"
            f"urgent:{'true' if t.get('urgent') else 'false'},wife:{'true' if t.get('wife') else 'false'}}},"
        )
    return "\n".join(lines)

def git_cmd(cmd):
    r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip() or r.stderr.strip()

# ── HONEY LIST CHANGE DETECTOR ────────────────────────────────────────────────
HONEY_STATE_FILE = Path("/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/honey-state.json")

def load_honey_state():
    try:
        return json.loads(HONEY_STATE_FILE.read_text()) if HONEY_STATE_FILE.exists() else []
    except:
        return []

def save_honey_state(items):
    try:
        HONEY_STATE_FILE.write_text(json.dumps(items))
    except:
        pass

def notify_new_honey_items(current_items, previous_items):
    prev_set = set(previous_items)
    new_items = [item for item in current_items if item not in prev_set]
    for item in new_items:
        short = item[:60] + ("…" if len(item) > 60 else "")
        script = f'display notification "{short}" with title "💌 Cindy added to her list" sound name "Glass"'
        subprocess.run(["osascript", "-e", script])
        print(f"   🔔 Notified: {short}")
    return new_items

# ── READ & PARSE ───────────────────────────────────────────────────────────────
vault_text = VAULT_FILE.read_text(encoding="utf-8") if VAULT_FILE.exists() else ""
honey_text = HONEY_FILE.read_text(encoding="utf-8") if HONEY_FILE.exists() else ""

urgent_tasks  = parse_tasks(vault_text, "🔥 Time-Sensitive")
quick_tasks   = parse_tasks(vault_text, "⚡ Quick Wins")
project_tasks = parse_tasks(vault_text, "🎯 Active Projects")
waiting_tasks = parse_tasks(vault_text, "⏳ Waiting On Others")
someday_tasks = parse_tasks(vault_text, "💭 Someday")
vault_events  = parse_vault_events(vault_text)
honey_events  = parse_honey_events(honey_text)
honey_todos   = parse_wife_checkboxes(honey_text)

# ── HONEY LIST NOTIFICATIONS ──────────────────────────────────────────────────
previous_honey   = load_honey_state()
new_items        = notify_new_honey_items(honey_todos, previous_honey)
if new_items:
    save_honey_state(honey_todos)
elif not previous_honey:
    save_honey_state(honey_todos)  # First run — save baseline

all_events       = collect_events(vault_events, honey_events)
calendar_html    = build_calendar_html(all_events)
event_cards_html = build_event_cards_html(all_events)
all_tasks_js     = "\n".join([
    tasks_to_js(urgent_tasks,  "urgent",   100),
    tasks_to_js(quick_tasks,   "quick",    200),
    tasks_to_js(project_tasks, "projects", 300),
    tasks_to_js(waiting_tasks, "waiting",  400),
    tasks_to_js(someday_tasks, "someday",  500),
])
now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

# ── HTML ───────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>LifeLedger — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0e0e0f; --bg2:#161618; --bg3:#1e1e21;
  --border:rgba(255,255,255,0.07); --border2:rgba(255,255,255,0.14);
  --text:#e8e6e0; --text2:#888680; --text3:#4a4845;
  --gold:#d4a843; --red:#e05c4b; --green:#4caf7d; --purple:#9b7fe8;
  --pink:#e87fa0; --pink-bg:rgba(232,127,160,0.08); --pink-bd:rgba(232,127,160,0.25);
  --mono:'DM Mono',monospace; --dis:'Syne',sans-serif;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;line-height:1.6;min-height:100vh;}}

/* ── HEADER ── */
.hdr{{border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:var(--bg);z-index:100;}}
.logo{{font-family:var(--dis);font-weight:800;font-size:16px;letter-spacing:-0.02em;display:flex;align-items:center;gap:9px;}}
.ldot{{width:6px;height:6px;background:var(--gold);border-radius:50%;animation:pulse 2s ease-in-out infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1);}}50%{{opacity:0.5;transform:scale(0.8);}}}}
.hmeta{{font-size:10px;color:var(--text3);}}
.spill{{background:rgba(76,175,125,0.12);border:1px solid rgba(76,175,125,0.25);color:var(--green);font-size:11px;padding:3px 10px;border-radius:2px;}}

/* ── WIFE BANNER ── */
.wbanner{{background:var(--pink-bg);border-bottom:1px solid var(--pink-bd);padding:11px 28px;}}
.wtitle{{font-family:var(--dis);font-size:11px;font-weight:700;color:var(--pink);margin-bottom:8px;letter-spacing:0.02em;}}
.wgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:5px;}}
.wi{{background:rgba(232,127,160,0.05);border:1px solid var(--pink-bd);border-radius:3px;padding:6px 9px;cursor:pointer;transition:background 0.15s;}}
.wi:hover{{background:rgba(232,127,160,0.12);}}
.wi.done{{opacity:0.3;}}
.wi.done .wit{{text-decoration:line-through;color:var(--text3);}}
.wirow{{display:flex;gap:6px;align-items:center;}}
.wck{{width:11px;height:11px;border:1.5px solid var(--pink-bd);border-radius:2px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}}
.wck.on{{background:var(--pink);border-color:var(--pink);}}
.wck svg{{opacity:0;}}.wck.on svg{{opacity:1;}}
.wit{{font-size:11px;color:var(--text);line-height:1.3;}}

/* ── CALENDAR + EVENTS WRAPPER ── */
.cal-wrap{{display:grid;grid-template-columns:1fr 380px;border-bottom:1px solid var(--border);min-height:420px;}}
.cal-main{{padding:18px 28px;border-right:1px solid var(--border);overflow:hidden;}}
.sec-label{{font-family:var(--dis);font-size:9px;font-weight:700;color:var(--text3);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px;}}
.cal-months{{display:flex;gap:24px;flex-wrap:wrap;}}

/* ── MONTH GRID ── */
.cal-month{{flex:1;min-width:280px;}}
.cal-mname{{font-family:var(--dis);font-size:15px;font-weight:700;color:var(--text);margin-bottom:10px;}}
.cgrid{{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;}}
.cdow{{font-size:9px;color:var(--text3);text-align:center;padding:2px 0;font-family:var(--mono);}}
.ccell{{min-height:64px;padding:4px 4px 3px;background:var(--bg2);border-radius:2px;border:1px solid transparent;transition:all 0.12s;cursor:default;overflow:hidden;}}
.ccell:hover{{background:var(--bg3);border-color:var(--border2);}}
.cempty{{background:transparent!important;border:none!important;}}
.cpast{{opacity:0.3;}}
.ctoday{{background:rgba(212,168,67,0.1)!important;border-color:rgba(212,168,67,0.35)!important;}}
.cdaynum{{font-family:var(--dis);font-size:12px;font-weight:600;color:var(--text2);display:block;line-height:1;}}
.ctoday .cdaynum{{color:var(--gold);}}
.cdots{{display:flex;gap:2px;margin:2px 0 1px;flex-wrap:wrap;}}
.cdot{{width:6px;height:6px;border-radius:50%;flex-shrink:0;}}
.cdot-urg{{background:var(--red);}}
.cdot-soon{{background:var(--gold);}}
.cdot-upcoming{{background:var(--purple);}}
.cdot-future{{background:var(--border2);}}
.cdot-wife{{background:var(--pink);}}
.clbl{{font-size:9px;line-height:1.3;padding:1px 3px;border-radius:1px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;max-width:100%;margin-top:2px;}}
.clbl-urg{{background:rgba(224,92,75,0.18);color:var(--red);}}
.clbl-soon{{background:rgba(212,168,67,0.15);color:var(--gold);}}
.clbl-upcoming{{background:rgba(155,127,232,0.15);color:var(--purple);}}
.clbl-future{{background:rgba(255,255,255,0.05);color:var(--text3);}}
.clbl-wife{{background:rgba(232,127,160,0.18);color:var(--pink);}}
.cal-legend{{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;}}
.leg{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--text3);}}
.ldot2{{width:6px;height:6px;border-radius:50%;}}

/* ── EVENT CARDS ── */
.ev-side{{padding:18px 18px;overflow-y:auto;max-height:460px;}}
.ev-side::-webkit-scrollbar{{width:3px;}}
.ev-side::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:2px;}}
.evlist{{display:flex;flex-direction:column;gap:6px;}}
.evc{{background:var(--bg3);border:1px solid var(--border);border-radius:3px;padding:9px 11px;border-left:3px solid var(--border2);transition:all 0.12s;}}
.evc:hover{{transform:translateX(2px);}}
.ev-urg{{border-left-color:var(--red);background:rgba(224,92,75,0.07);}}
.ev-soon{{border-left-color:var(--gold);background:rgba(212,168,67,0.05);}}
.ev-upcoming{{border-left-color:var(--purple);background:rgba(155,127,232,0.05);}}
.ev-future{{border-left-color:var(--border2);}}
.ev-wife{{border-left-color:var(--pink)!important;background:rgba(232,127,160,0.06)!important;}}
.evc-top{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;gap:6px;}}
.evc-date{{font-family:var(--dis);font-size:11px;font-weight:700;color:var(--text2);}}
.ev-urg .evc-date{{color:var(--red);}}
.ev-soon .evc-date{{color:var(--gold);}}
.ev-upcoming .evc-date{{color:var(--purple);}}
.ev-wife .evc-date{{color:var(--pink)!important;}}
.evc-cd{{font-family:var(--mono);font-size:10px;color:var(--text3);white-space:nowrap;}}
.ev-urg .evc-cd{{color:var(--red);font-weight:500;}}
.ev-soon .evc-cd{{color:var(--gold);}}
.ev-wife .evc-cd{{color:var(--pink)!important;}}
.evc-title{{font-size:11px;color:var(--text);line-height:1.4;}}

/* ── STATS ── */
.stats{{display:grid;grid-template-columns:repeat(5,1fr);border-bottom:1px solid var(--border);}}
.stat{{padding:13px 20px;border-right:1px solid var(--border);}}
.stat:last-child{{border-right:none;}}
.slbl{{font-size:9px;color:var(--text3);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;}}
.sval{{font-family:var(--dis);font-size:24px;font-weight:700;color:var(--text);line-height:1;}}
.sval.red{{color:var(--red);}}.sval.green{{color:var(--green);}}.sval.gold{{color:var(--gold);}}.sval.pink{{color:var(--pink);}}
.ssub{{font-size:9px;color:var(--text3);margin-top:2px;}}

/* ── TOOLBAR ── */
.toolbar{{padding:9px 28px;display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--border);flex-wrap:wrap;}}
.tl{{font-size:10px;color:var(--text3);letter-spacing:0.1em;text-transform:uppercase;margin-right:2px;}}
.fb{{font-family:var(--mono);font-size:11px;padding:4px 10px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;border-radius:2px;transition:all 0.15s;}}
.fb:hover{{border-color:var(--gold);color:var(--gold);}}
.fb.on{{border-color:var(--gold);background:rgba(212,168,67,0.1);color:var(--gold);}}
.fb.wf{{border-color:var(--pink-bd);color:var(--pink);}}
.fb.wf.on{{background:var(--pink-bg);border-color:var(--pink);}}
.sp{{flex:1;}}
.pw{{display:flex;align-items:center;gap:8px;}}
.pl{{font-size:10px;color:var(--text3);}}
.pt{{width:80px;height:3px;background:var(--bg3);border-radius:2px;overflow:hidden;}}
.pf{{height:100%;background:var(--green);border-radius:2px;transition:width 0.4s;}}
.pp{{font-size:11px;color:var(--green);min-width:26px;}}

/* ── BOARD ── */
.main{{padding:18px 28px;}}
.board{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;}}
.col{{display:flex;flex-direction:column;gap:6px;}}
.ch{{display:flex;align-items:center;justify-content:space-between;padding:0 0 6px;border-bottom:1px solid var(--border);margin-bottom:2px;}}
.ct{{font-family:var(--dis);font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:var(--text2);display:flex;align-items:center;gap:5px;}}
.cc{{font-size:10px;color:var(--text3);background:var(--bg3);padding:2px 7px;border-radius:2px;min-width:20px;text-align:center;}}
.cc.hot{{background:rgba(224,92,75,0.15);color:var(--red);}}
.card{{background:var(--bg2);border:1px solid var(--border);border-radius:3px;padding:9px 11px;cursor:pointer;transition:all 0.15s;position:relative;overflow:hidden;}}
.card::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:2px;background:transparent;transition:background 0.15s;}}
.card:hover{{border-color:var(--border2);background:var(--bg3);}}
.card:hover::before{{background:var(--gold);}}
.card.done{{opacity:0.28;}}.card.done .ct2{{text-decoration:line-through;color:var(--text3);}}
.card.urg{{border-color:rgba(224,92,75,0.2);}}.card.urg::before{{background:rgba(224,92,75,0.6)!important;}}
.card.wc{{border-color:var(--pink-bd);}}.card.wc::before{{background:var(--pink)!important;}}
.cr{{display:flex;align-items:flex-start;gap:8px;}}
.ck{{width:12px;height:12px;border:1.5px solid var(--border2);border-radius:2px;flex-shrink:0;margin-top:1px;display:flex;align-items:center;justify-content:center;}}
.ck.on{{background:var(--green);border-color:var(--green);}}
.ck svg{{opacity:0;}}.ck.on svg{{opacity:1;}}
.ct2{{font-size:12px;color:var(--text);line-height:1.5;flex:1;}}
.ctags{{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px;padding-left:20px;}}
.tag{{font-size:9px;letter-spacing:0.05em;text-transform:uppercase;padding:1px 5px;border-radius:1px;font-weight:500;}}
.tm{{background:rgba(76,175,125,0.12);color:#4caf7d;border:1px solid rgba(76,175,125,0.2);}}
.th{{background:rgba(212,168,67,0.1);color:#c9a03a;border:1px solid rgba(212,168,67,0.2);}}
.ti{{background:rgba(155,127,232,0.1);color:#9b7fe8;border:1px solid rgba(155,127,232,0.2);}}
.tr{{background:rgba(232,127,155,0.1);color:#e87f9b;border:1px solid rgba(232,127,155,0.2);}}
.tmed{{background:rgba(63,168,154,0.1);color:#3fa89a;border:1px solid rgba(63,168,154,0.2);}}
.tf{{background:rgba(136,134,128,0.1);color:#888680;border:1px solid rgba(136,134,128,0.2);}}
.ts{{background:rgba(100,130,200,0.1);color:#6482c8;border:1px solid rgba(100,130,200,0.2);}}
.tw{{background:rgba(232,127,160,0.12);color:var(--pink);border:1px solid var(--pink-bd);}}
.sd{{display:flex;align-items:center;gap:12px;margin:8px 0 12px;}}
.sdt{{font-family:var(--dis);font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text3);white-space:nowrap;}}
.sdl{{flex:1;height:1px;background:var(--border);}}
.sg{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;}}
.sg .card{{padding:7px 10px;}}
.wg{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;}}
.footer{{margin-top:24px;padding:12px 28px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}}
.fn{{font-size:10px;color:var(--text3);}}
.fl{{font-size:10px;color:var(--gold);text-decoration:none;opacity:0.6;}}
.fl:hover{{opacity:1;}}
::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:2px;}}
@media(max-width:960px){{
  .cal-wrap{{grid-template-columns:1fr;}}
  .cal-main{{border-right:none;border-bottom:1px solid var(--border);}}
  .wgrid{{grid-template-columns:repeat(2,1fr);}}
  .board{{grid-template-columns:1fr;}}
  .stats{{grid-template-columns:repeat(3,1fr);}}
}}
</style>
</head>
<body>

<header class="hdr">
  <div class="logo"><div class="ldot"></div>LifeLedger</div>
  <div style="display:flex;align-items:center;gap:14px;">
    <span class="hmeta">Updated {now}</span>
    <span class="spill">$132/mo saved</span>
  </div>
</header>

<div class="wbanner">
  <div class="wtitle">💌 Wife Priority — Two-Week Protocol · started 03/30/26 · ends ~04/13/26</div>
  <div class="wgrid" id="wg"></div>
</div>

<div class="cal-wrap">
  <div class="cal-main">
    <div class="sec-label">📅 Calendar</div>
    <div class="cal-months">
      {calendar_html}
    </div>
    <div class="cal-legend">
      <div class="leg"><div class="ldot2" style="background:var(--red)"></div>≤3 days</div>
      <div class="leg"><div class="ldot2" style="background:var(--gold)"></div>This week</div>
      <div class="leg"><div class="ldot2" style="background:var(--purple)"></div>2 weeks</div>
      <div class="leg"><div class="ldot2" style="background:var(--pink)"></div>Wife / together</div>
      <div class="leg"><div class="ldot2" style="background:var(--border2)"></div>Future</div>
    </div>
  </div>
  <div class="ev-side">
    <div class="sec-label" style="margin-bottom:10px;">Upcoming</div>
    <div class="evlist">
      {event_cards_html}
    </div>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="slbl">Open tasks</div><div class="sval" id="s-open">0</div><div class="ssub">all sections</div></div>
  <div class="stat"><div class="slbl">Time-sensitive</div><div class="sval red" id="s-urg">0</div><div class="ssub">need action now</div></div>
  <div class="stat"><div class="slbl">Wife priority</div><div class="sval pink" id="s-wife">0</div><div class="ssub">protocol remaining</div></div>
  <div class="stat"><div class="slbl">$ items</div><div class="sval green" id="s-money">0</div><div class="ssub">savings / income</div></div>
  <div class="stat"><div class="slbl">Done today</div><div class="sval green" id="s-done">0</div><div class="ssub">this session</div></div>
</div>

<div class="toolbar">
  <span class="tl">Filter</span>
  <button class="fb on"  onclick="sf('all',this)">All</button>
  <button class="fb wf"  onclick="sf('wife',this)">💌 Wife</button>
  <button class="fb"     onclick="sf('money',this)">$ Money</button>
  <button class="fb"     onclick="sf('home',this)">Home</button>
  <button class="fb"     onclick="sf('income',this)">Income</button>
  <button class="fb"     onclick="sf('family',this)">Family</button>
  <button class="fb"     onclick="sf('medical',this)">Medical</button>
  <button class="fb"     onclick="sf('romance',this)">Romance</button>
  <div class="sp"></div>
  <div class="pw"><span class="pl">Session</span><div class="pt"><div class="pf" id="prog" style="width:0%"></div></div><span class="pp" id="pct">0%</span></div>
</div>

<div class="main">
  <div class="board">
    <div class="col"><div class="ch"><div class="ct">🔥 Time-sensitive</div><span class="cc hot" id="c-urg">0</span></div><div id="col-urg"></div></div>
    <div class="col"><div class="ch"><div class="ct">⚡ Quick wins</div><span class="cc" id="c-quick">0</span></div><div id="col-quick"></div></div>
    <div class="col"><div class="ch"><div class="ct">🎯 Active projects</div><span class="cc" id="c-proj">0</span></div><div id="col-proj"></div></div>
  </div>
  <div class="sd"><span class="sdt">⏳ Waiting on others</span><div class="sdl"></div><span class="cc" id="c-wait">0</span></div>
  <div class="wg" id="col-wait"></div>
  <div class="sd" style="margin-top:16px"><span class="sdt">💭 Someday</span><div class="sdl"></div><span class="cc" id="c-some">0</span></div>
  <div class="sg" id="col-some"></div>
</div>

<footer class="footer">
  <span class="fn">Auto-refreshes every 5 min · the-daily-ops.netlify.app</span>
  <a class="fl" href="#" onclick="location.reload()">↺ refresh</a>
</footer>

<script>
const CHK='<svg width="8" height="6" viewBox="0 0 8 6" fill="none"><path d="M1 3L3 5L7 1" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const WIFE={json.dumps(honey_todos,ensure_ascii=False)}.filter(Boolean).map((t,i)=>({{id:'h'+i,title:t}}));
const TASKS=[
{all_tasks_js}
];
const done=new Set(JSON.parse(localStorage.getItem('ll-done')||'[]'));
const wd=new Set(JSON.parse(localStorage.getItem('ll-wife-done')||'[]'));
let af='all';
const TC={{home:'th',income:'ti',romance:'tr',medical:'tmed',family:'tf',self:'ts',wife:'tw'}};
function matches(t){{if(af==='all')return true;if(af==='money')return t.money;if(af==='wife')return t.wife||t.tags.includes('wife');return t.tags.includes(af);}}
function tagH(t){{const p=[];if(t.money)p.push('<span class="tag tm">$</span>');(t.tags||[]).forEach(g=>p.push(`<span class="tag ${{TC[g]||'tf'}}">${{g}}</span>`));return p.length?`<div class="ctags">${{p.join('')}}</div>`:''}}
function cardH(t){{const d=done.has(t.id),cls=[d?'done':'',t.urgent&&!d?'urg':'',t.wife&&!d?'wc':''].filter(Boolean).join(' ');return`<div class="card ${{cls}}" onclick="tog(${{t.id}})"><div class="cr"><div class="ck${{d?' on':''}}">${{d?CHK:''}}</div><span class="ct2">${{t.title}}</span></div>${{tagH(t)}}</div>`;}}
function wifeH(w){{const d=wd.has(w.id);return`<div class="wi${{d?' done':''}}" onclick="togW('${{w.id}}')"><div class="wirow"><div class="wck${{d?' on':''}}">${{d?CHK:''}}</div><span class="wit">${{w.title}}</span></div></div>`;}}
function render(){{
  document.getElementById('wg').innerHTML=WIFE.map(wifeH).join('');
  const cols={{urg:'urgent',quick:'quick',proj:'projects',wait:'waiting',some:'someday'}};
  for(const[k,col]of Object.entries(cols)){{
    const ts=TASKS.filter(t=>t.col===col&&matches(t));
    document.getElementById('col-'+k).innerHTML=ts.map(cardH).join('');
    document.getElementById('c-'+k).textContent=ts.filter(t=>!done.has(t.id)).length;
  }}
  document.getElementById('s-wife').textContent=WIFE.filter(w=>!wd.has(w.id)).length;
  document.getElementById('s-open').textContent=TASKS.filter(matches).filter(t=>!done.has(t.id)).length;
  document.getElementById('s-urg').textContent=TASKS.filter(t=>t.col==='urgent'&&!done.has(t.id)).length;
  document.getElementById('s-money').textContent=TASKS.filter(t=>t.money&&!done.has(t.id)).length;
  const td=done.size+wd.size,tot=TASKS.length+WIFE.length;
  document.getElementById('s-done').textContent=td;
  const p=Math.round(td/tot*100);
  document.getElementById('prog').style.width=p+'%';
  document.getElementById('pct').textContent=p+'%';
}}
function tog(id){{done.has(id)?done.delete(id):done.add(id);localStorage.setItem('ll-done',JSON.stringify([...done]));render();}}
function togW(id){{wd.has(id)?wd.delete(id):wd.add(id);localStorage.setItem('ll-wife-done',JSON.stringify([...wd]));render();}}
function sf(f,btn){{af=f;document.querySelectorAll('.fb').forEach(b=>b.classList.remove('on'));btn.classList.add('on');render();}}
render();
</script>
</body>
</html>"""

OUTPUT_FILE.write_text(html, encoding="utf-8")
print(f"✅ Dashboard updated — {now}")
print(f"   Calendar: {len(all_events)} events ({len(vault_events)} vault + {len(honey_events)} honey)")
print(f"   Wife banner: {len(honey_todos)} items (test entries filtered)")
print(f"   Tasks: {len(urgent_tasks)} urgent · {len(quick_tasks)} quick · {len(project_tasks)} projects")

# ── PUBLISH TO GITHUB PAGES ───────────────────────────────────────────────────
print("\n→ Publishing to GitHub Pages...")
git_cmd(["git","add","dashboard.html","lifeledger-viewer.html","index.html"])
ok, out = git_cmd(["git","commit","-m",f"Auto-refresh {now}"])
if "nothing to commit" in out:
    print("   No changes — already up to date.")
else:
    ok, out = git_cmd(["git","push","origin","main"])
    print(f"   ✅ Live at: https://the-daily-ops.github.io/lifeledger/dashboard.html" if ok else f"   ⚠️  Push failed: {out}")
