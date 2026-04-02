#!/usr/bin/env python3
"""
LifeLedger Viewer Generator
============================
Reads all .md records in the LifeLedger folder → writes lifeledger-viewer.html → pushes to GitHub.
Run anytime: python3 generate-viewer.py  (alias: viewer)
No Claude needed. Zero AI tokens.

To add a new record: create a .md file in the right folder, then run: viewer
"""

import re, subprocess
from pathlib import Path
from datetime import datetime

# ── PATHS ──────────────────────────────────────────────────────────────────────
BASE        = Path("/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger")
OUTPUT_FILE = BASE / "lifeledger-viewer.html"
REPO_DIR    = str(BASE)

FOLDERS = [
    ("CostSavings",     "💰", "Cost Savings",     "green"),
    ("Finances",        "📊", "Finances",          "gold"),
    ("HomeImprovement", "🏠", "Home Improvement",  "amber"),
    ("Medical",         "🏥", "Medical",           "teal"),
    ("Vehicles",        "🚗", "Vehicles",          "blue"),
    ("WorkBenefits",    "💼", "Work Benefits",     "slate"),
    ("Journal",         "📓", "Journal",           "grey"),
]

NOW = datetime.now().strftime("%B %d, %Y at %I:%M %p")

# ── MARKDOWN PARSER ────────────────────────────────────────────────────────────
def parse_record(path: Path) -> dict:
    text  = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rec = {
        "filename": path.name, "title": "", "date": "", "status": "",
        "category": "", "type": "", "monthly_savings": 0.0,
        "onetime_amount": 0.0, "body_html": "",
        "is_wife": False, "is_warn": False, "is_pending": False,
    }
    for line in lines:
        if line.startswith("# ") and not rec["title"]:
            rec["title"] = line.lstrip("# ").strip()
        m = re.match(r"\*\*Date[^:]*:\*\*\s*(.+)", line)
        if m: rec["date"] = m.group(1).strip()
        m = re.match(r"\*\*Status[^:]*:\*\*\s*(.+)", line)
        if m: rec["status"] = m.group(1).strip()
        m = re.match(r"\*\*Category[^:]*:\*\*\s*(.+)", line)
        if m: rec["category"] = m.group(1).strip()
        m = re.match(r"\*\*Type[^:]*:\*\*\s*(.+)", line)
        if m: rec["type"] = m.group(1).strip()
        m = re.match(r"\*\*Monthly Savings[^:]*:\*\*\s*\$?([\d,.]+)", line)
        if m:
            try: rec["monthly_savings"] = float(m.group(1).replace(",", ""))
            except: pass
        m = re.match(r"\*\*One-Time Amount[^:]*:\*\*\s*\$?([\d,.]+)", line)
        if m:
            try: rec["onetime_amount"] = float(m.group(1).replace(",", ""))
            except: pass
    t = rec["title"].lower() + rec["status"].lower()
    rec["is_wife"]    = "wife" in t or "💌" in rec["title"] or "🌸" in rec["status"]
    rec["is_warn"]    = "⚠" in text or "red flag" in text.lower()
    rec["is_pending"] = any(w in rec["status"].lower() for w in ["pending","in progress","in transit","waiting"])
    rec["body_html"]  = md_to_html(text)
    return rec

def inline_md(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>",         text)
    text = re.sub(r"`(.+?)`",       r"<code>\1</code>",      text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text

def render_table(rows):
    if not rows: return ""
    html = ['<table class="row-table">']
    for i, row in enumerate(rows):
        tag = "th" if i == 0 else "td"
        html.append("<tr>" + "".join(f"<{tag}>{inline_md(c)}</{tag}>" for c in row) + "</tr>")
    html.append("</table>")
    return "\n".join(html)

SKIP_META = re.compile(r"\*\*(Date|Status|Category|Provider|Duration|Owner|Type|Monthly Savings|One-Time Amount)[^:]*:\*\*")

def md_to_html(text):
    lines, parts, in_table, table_rows, i = text.splitlines(), [], False, [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# ") or SKIP_META.match(line):
            i += 1; continue
        if line.strip() in ("---", "***", "___"):
            if in_table: parts.append(render_table(table_rows)); table_rows = []; in_table = False
            i += 1; continue
        if line.strip().startswith("|"):
            in_table = True
            if not re.match(r"^\|[-| :]+\|$", line.strip()):
                table_rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            i += 1; continue
        else:
            if in_table: parts.append(render_table(table_rows)); table_rows = []; in_table = False
        if   line.startswith("## "):  parts.append(f'<div class="rb-heading">{line.lstrip("# ").strip()}</div>')
        elif line.startswith("### "): parts.append(f'<div class="rb-subheading">{line.lstrip("# ").strip()}</div>')
        elif line.startswith("> "):   parts.append(f'<div class="note-box">{inline_md(line[2:])}</div>')
        elif line.strip().startswith("⚠"): parts.append(f'<div class="warn-box">{inline_md(line.strip())}</div>')
        elif re.match(r"^[\s]*- \[ \]", line):
            c = re.sub(r"^[\s]*- \[ \]\s*", "", line)
            parts.append(f'<div class="rb-check">☐ {inline_md(c)}</div>')
        elif re.match(r"^[\s]*- \[x\]", line, re.I):
            c = re.sub(r"^[\s]*- \[x\]\s*", "", line, flags=re.I)
            parts.append(f'<div class="rb-check done">☑ {inline_md(c)}</div>')
        elif re.match(r"^[\s]*[-*]\s+", line):
            indent = len(line) - len(line.lstrip())
            cls = "rb-bullet-sub" if indent > 0 else "rb-bullet"
            c = re.sub(r"^[\s]*[-*]\s+", "", line)
            parts.append(f'<div class="{cls}">· {inline_md(c)}</div>')
        elif re.match(r"^\d+\.\s+", line):
            c = re.sub(r"^\d+\.\s+", "", line)
            parts.append(f'<div class="rb-bullet">· {inline_md(c)}</div>')
        elif line.strip():
            parts.append(f'<p class="rb-para">{inline_md(line.strip())}</p>')
        i += 1
    if in_table: parts.append(render_table(table_rows))
    return "\n".join(parts)

# ── SAVINGS BANNER ─────────────────────────────────────────────────────────────
def build_savings_banner(folder_path: Path) -> str:
    records = sorted(folder_path.glob("*.md"), reverse=True)
    recurring_total, onetime_total = 0.0, 0.0
    recurring_wins, onetime_wins   = [], []
    for r in records:
        rec = parse_record(r)
        t   = rec["type"].lower()
        if "recurring" in t:
            recurring_total += rec["monthly_savings"]
            if rec["monthly_savings"] > 0:
                recurring_wins.append((rec["title"], rec["monthly_savings"]))
        elif "one-time" in t or "onetime" in t:
            onetime_total += rec["onetime_amount"]
            if rec["onetime_amount"] > 0:
                onetime_wins.append((rec["title"], rec["onetime_amount"]))
    annual = recurring_total * 12

    rec_rows = "".join(
        f'<div class="sw-row"><span class="sw-name">{t}</span>'
        f'<span class="sw-amt sw-green">${a:.0f}/mo</span></div>'
        for t, a in recurring_wins
    ) or '<div class="sw-row sw-empty">None logged yet</div>'

    one_rows = "".join(
        f'<div class="sw-row"><span class="sw-name">{t}</span>'
        f'<span class="sw-amt sw-gold">${a:.2f}</span></div>'
        for t, a in onetime_wins
    ) or '<div class="sw-row sw-empty">None logged yet</div>'

    return (
        '<div class="savings-banner">'
        '<div class="sb-tiles">'
        f'<div class="sb-tile sb-recurring">'
        f'<div class="sb-label">💚 Recurring savings</div>'
        f'<div class="sb-val">${recurring_total:.0f}<span class="sb-unit">/mo</span></div>'
        f'<div class="sb-sub">${annual:.0f}/yr projected</div>'
        f'</div>'
        f'<div class="sb-tile sb-onetime">'
        f'<div class="sb-label">✨ One-time wins</div>'
        f'<div class="sb-val">${onetime_total:.2f}</div>'
        f'<div class="sb-sub">cash back · returns · credits</div>'
        f'</div>'
        f'<div class="sb-tile sb-total">'
        f'<div class="sb-label">🏆 Total value captured</div>'
        f'<div class="sb-val">${(onetime_total + annual):.0f}</div>'
        f'<div class="sb-sub">one-time + 12 months recurring</div>'
        f'</div>'
        f'</div>'
        f'<div class="sb-breakdown">'
        f'<div class="sb-col"><div class="sb-col-head">Recurring wins</div>{rec_rows}</div>'
        f'<div class="sb-col"><div class="sb-col-head">One-time wins</div>{one_rows}</div>'
        f'</div>'
        f'</div>'
    )

# ── SECTIONS ───────────────────────────────────────────────────────────────────
def build_sections(folders):
    sidebar_html, section_html, overview_cards = [], [], []
    sidebar_html.append(
        '<div class="sidebar-item active" onclick="showSection(\'overview\',null,this)">'
        '<span class="sidebar-item-name">🗂 Overview</span></div>'
    )
    for folder_name, icon, label, _ in folders:
        folder_path = BASE / folder_name
        if not folder_path.exists(): continue
        records = sorted(folder_path.glob("*.md"), reverse=True)
        if not records: continue
        parsed = [parse_record(r) for r in records]
        count  = len(parsed)
        sec_id = folder_name.lower()

        sidebar_html.append(
            f'<div class="sidebar-item" onclick="showSection(\'{sec_id}\',null,this)">'
            f'<span class="sidebar-item-name">{icon} {label}</span>'
            f'<span class="sidebar-count">{count}</span></div>'
        )
        preview = " · ".join(r["title"][:28] for r in parsed[:3])
        overview_cards.append(
            f'<div class="ov-card {sec_id}" onclick="showSection(\'{sec_id}\')">'
            f'<div class="ov-icon">{icon}</div>'
            f'<div class="ov-title">{label}</div>'
            f'<div class="ov-count">{count} record{"s" if count!=1 else ""}</div>'
            f'<div class="ov-preview">{preview}</div></div>'
        )

        cards = []
        for rec in parsed:
            if rec["is_wife"]:
                badge = '<span class="badge badge-wife">🌸 Wife priority</span>'
            elif "✅" in rec["status"] or "complete" in rec["status"].lower() or "resolved" in rec["status"].lower():
                badge = '<span class="badge badge-done">✓ Complete</span>'
            elif rec["is_pending"]:
                badge = '<span class="badge badge-pending">⏳ Pending</span>'
            elif rec["is_warn"]:
                badge = '<span class="badge badge-warn">⚠ Review</span>'
            else:
                badge = ""

            money_badge = ""
            if folder_name == "CostSavings" and rec["type"]:
                if "recurring" in rec["type"].lower() and rec["monthly_savings"]:
                    money_badge = f'<span class="badge badge-money">${rec["monthly_savings"]:.0f}/mo</span>'
                elif rec["onetime_amount"]:
                    money_badge = f'<span class="badge badge-money">${rec["onetime_amount"]:.2f}</span>'

            card_cls = "record wife-record" if rec["is_wife"] else "record"
            open_cls = " open" if rec["is_wife"] else ""
            cat_str  = f' · {rec["category"]}' if rec["category"] else ""
            cards.append(
                f'<div class="{card_cls}{open_cls}">'
                f'<div class="record-header" onclick="toggleRecord(this)">'
                f'<div><div class="record-title">{rec["title"]}</div>'
                f'<div class="record-date">{rec["date"]}{cat_str}</div></div>'
                f'<div class="record-badges">{money_badge}{badge}'
                f'<span class="chevron">▼</span></div></div>'
                f'<div class="record-body">{rec["body_html"]}</div>'
                f'</div>'
            )

        banner = build_savings_banner(folder_path) if folder_name == "CostSavings" else ""
        section_html.append(
            f'<div class="section" id="sec-{sec_id}">'
            f'<div class="section-header">'
            f'<div class="section-title">{label}</div>'
            f'<div class="section-meta">{count} record{"s" if count!=1 else ""} · updated {NOW}</div>'
            f'</div>{banner}'
            f'<div class="records">{"".join(cards)}</div></div>'
        )

    total = sum(len(list((BASE/f).glob("*.md"))) for f,_,_,_ in folders if (BASE/f).exists())
    ov = (
        f'<div class="section active" id="sec-overview">'
        f'<div class="section-header">'
        f'<div class="section-title">Your Records</div>'
        f'<div class="section-meta">{total} files · updated {NOW}</div></div>'
        f'<div class="overview-grid">{"".join(overview_cards)}</div>'
        f'<div class="add-tip"><div class="add-tip-label">To add a new record</div>'
        f'<div class="add-tip-cmd">Create a .md file in the right folder, then run: <strong>viewer</strong></div></div>'
        f'</div>'
    )
    return sidebar_html, [ov] + section_html, total

# ── HTML ────────────────────────────────────────────────────────────────────────
def build_html(sidebar_items, sections, total_records):
    sidebar = "\n".join(sidebar_items)
    content = "\n".join(sections)
    n_folders = len([f for f,_,_,_ in FOLDERS if (BASE/f).exists()])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>LifeLedger — Records</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#f7f5f0; --bg2:#eeebe3; --bg3:#e5e1d6;
  --ink:#1a1814; --ink2:#5a5649; --ink3:#9a9488;
  --rule:rgba(26,24,20,0.1); --rule2:rgba(26,24,20,0.06);
  --gold:#b8882a; --red:#c0392b; --green:#2e7d52; --blue:#1a5276; --teal:#1a7070;
  --pink:#c9547a; --pink-bg:rgba(201,84,122,0.06); --pink-border:rgba(201,84,122,0.2);
  --serif:'Playfair Display',Georgia,serif;
  --sans:'DM Sans',system-ui,sans-serif;
  --mono:'DM Mono',monospace;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.65;}}
.masthead{{background:rgba(26,24,20,0.97);color:var(--bg);padding:16px 40px;display:flex;align-items:center;justify-content:space-between;}}
.masthead-title{{font-family:var(--serif);font-size:20px;font-weight:500;color:rgba(247,245,240,0.7);}}
.masthead-right{{font-family:var(--mono);font-size:10px;color:rgba(247,245,240,0.25);letter-spacing:0.08em;}}
.nav{{background:var(--ink);padding:0 40px;display:flex;overflow-x:auto;}}
.nav-btn{{font-family:var(--mono);font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:rgba(247,245,240,0.4);padding:12px 18px;background:none;border:none;cursor:pointer;border-bottom:2px solid transparent;transition:all 0.15s;white-space:nowrap;}}
.nav-btn:hover{{color:rgba(247,245,240,0.8);}}
.nav-btn.active{{color:var(--gold);border-bottom-color:var(--gold);}}
.summary-band{{background:var(--bg2);border-bottom:1px solid var(--rule);display:grid;grid-template-columns:repeat(4,1fr);}}
.sum-cell{{padding:16px 20px;border-right:1px solid var(--rule);}}
.sum-cell:last-child{{border-right:none;}}
.sum-label{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:5px;}}
.sum-val{{font-family:var(--serif);font-size:22px;font-weight:500;color:var(--ink);line-height:1;}}
.sum-val.gold{{color:var(--gold);}}
.sum-sub{{font-size:11px;color:var(--ink3);margin-top:2px;}}
.layout{{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 180px);}}
.sidebar{{background:var(--bg2);border-right:1px solid var(--rule);padding:24px 0;}}
.sidebar-heading{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.12em;text-transform:uppercase;padding:6px 20px 4px;}}
.sidebar-item{{display:flex;align-items:center;justify-content:space-between;padding:8px 20px;cursor:pointer;transition:background 0.12s;border-left:2px solid transparent;}}
.sidebar-item:hover{{background:var(--bg3);}}
.sidebar-item.active{{background:var(--bg);border-left-color:var(--gold);}}
.sidebar-item-name{{font-size:13px;color:var(--ink2);}}
.sidebar-item.active .sidebar-item-name{{color:var(--ink);font-weight:500;}}
.sidebar-count{{font-family:var(--mono);font-size:10px;color:var(--ink3);background:var(--bg3);padding:1px 6px;border-radius:2px;}}
.content{{padding:32px 40px;min-width:0;}}
.section{{display:none;}}.section.active{{display:block;}}
.section-header{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:24px;padding-bottom:12px;border-bottom:1px solid var(--rule);}}
.section-title{{font-family:var(--serif);font-size:26px;font-weight:500;letter-spacing:-0.01em;}}
.section-meta{{font-family:var(--mono);font-size:10px;color:var(--ink3);}}
/* SAVINGS BANNER */
.savings-banner{{margin-bottom:28px;}}
.sb-tiles{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px;}}
.sb-tile{{background:white;border:1px solid var(--rule);border-radius:3px;padding:20px 22px;border-top:3px solid var(--rule);}}
.sb-recurring{{border-top-color:var(--green);}}
.sb-onetime{{border-top-color:var(--gold);}}
.sb-total{{border-top-color:#5b4fcf;}}
.sb-label{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;}}
.sb-val{{font-family:var(--serif);font-size:34px;font-weight:600;color:var(--ink);line-height:1;}}
.sb-unit{{font-size:18px;font-weight:400;opacity:0.45;}}
.sb-sub{{font-size:11px;color:var(--ink3);margin-top:5px;}}
.sb-breakdown{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.sb-col{{background:white;border:1px solid var(--rule);border-radius:3px;padding:16px 18px;}}
.sb-col-head{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.1em;text-transform:uppercase;padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid var(--rule2);}}
.sw-row{{display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;border-bottom:1px solid var(--rule2);font-size:12px;}}
.sw-row:last-child{{border-bottom:none;}}
.sw-name{{color:var(--ink2);flex:1;margin-right:12px;line-height:1.4;}}
.sw-amt{{font-family:var(--mono);font-size:11px;font-weight:500;white-space:nowrap;}}
.sw-green{{color:var(--green);}}
.sw-gold{{color:var(--gold);}}
.sw-empty{{color:var(--ink3);font-style:italic;justify-content:flex-start;}}
/* RECORDS */
.records{{display:flex;flex-direction:column;gap:14px;}}
.record{{background:white;border:1px solid var(--rule);border-radius:3px;overflow:hidden;transition:border-color 0.15s;}}
.record:hover{{border-color:rgba(26,24,20,0.2);}}
.wife-record{{border-left:3px solid var(--pink);}}
.record-header{{padding:14px 18px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;cursor:pointer;user-select:none;}}
.record-header:hover{{background:rgba(26,24,20,0.02);}}
.record-title{{font-family:var(--serif);font-size:16px;font-weight:500;color:var(--ink);line-height:1.3;}}
.record-date{{font-family:var(--mono);font-size:10px;color:var(--ink3);margin-top:3px;}}
.record-badges{{display:flex;gap:6px;align-items:center;flex-shrink:0;}}
.badge{{font-family:var(--mono);font-size:9px;letter-spacing:0.07em;text-transform:uppercase;padding:3px 8px;border-radius:2px;white-space:nowrap;}}
.badge-done{{background:rgba(46,125,82,0.1);color:var(--green);border:1px solid rgba(46,125,82,0.2);}}
.badge-pending{{background:rgba(184,136,42,0.1);color:var(--gold);border:1px solid rgba(184,136,42,0.25);}}
.badge-warn{{background:rgba(192,57,43,0.08);color:var(--red);border:1px solid rgba(192,57,43,0.2);}}
.badge-money{{background:rgba(46,125,82,0.1);color:var(--green);border:1px solid rgba(46,125,82,0.2);}}
.badge-wife{{background:var(--pink-bg);color:var(--pink);border:1px solid var(--pink-border);}}
.chevron{{color:var(--ink3);font-size:11px;transition:transform 0.2s;flex-shrink:0;margin-top:3px;}}
.record.open .chevron{{transform:rotate(180deg);}}
.record-body{{display:none;padding:16px 18px;border-top:1px solid var(--rule2);}}
.record.open .record-body{{display:block;}}
.rb-heading{{font-family:var(--serif);font-size:15px;font-weight:500;color:var(--ink);margin:14px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--rule2);}}
.rb-subheading{{font-family:var(--mono);font-size:11px;color:var(--ink2);letter-spacing:0.06em;text-transform:uppercase;margin:12px 0 6px;}}
.rb-para{{font-size:13px;color:var(--ink2);line-height:1.6;margin:6px 0;}}
.rb-bullet,.rb-bullet-sub{{font-size:13px;color:var(--ink2);line-height:1.5;}}
.rb-bullet{{padding:2px 0 2px 12px;}}
.rb-bullet-sub{{padding:2px 0 2px 24px;font-size:12px;color:var(--ink3);}}
.rb-check{{font-size:12px;color:var(--ink2);padding:2px 0 2px 12px;}}
.rb-check.done{{color:var(--green);opacity:0.65;text-decoration:line-through;}}
.row-table{{width:100%;border-collapse:collapse;margin:10px 0;font-size:12px;}}
.row-table th{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.08em;text-transform:uppercase;text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);background:var(--bg2);}}
.row-table td{{padding:7px 10px;border-bottom:1px solid var(--rule2);color:var(--ink2);vertical-align:top;}}
.row-table tr:last-child td{{border-bottom:none;}}
.note-box{{background:var(--bg2);border-left:3px solid var(--gold);padding:10px 14px;margin:10px 0;font-size:12px;color:var(--ink2);line-height:1.6;border-radius:0 2px 2px 0;}}
.warn-box{{background:rgba(192,57,43,0.06);border-left:3px solid var(--red);padding:10px 14px;margin:10px 0;font-size:12px;color:var(--red);line-height:1.6;border-radius:0 2px 2px 0;}}
code{{font-family:var(--mono);font-size:11px;background:var(--bg3);padding:1px 5px;border-radius:2px;color:var(--ink2);}}
strong{{font-weight:600;color:var(--ink);}}
.overview-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;}}
.ov-card{{background:white;border:1px solid var(--rule);border-radius:3px;padding:16px 18px;cursor:pointer;transition:all 0.15s;border-top:3px solid transparent;}}
.ov-card:hover{{border-color:rgba(26,24,20,0.15);transform:translateY(-1px);}}
.ov-card.costsavings{{border-top-color:var(--green);}}
.ov-card.finances{{border-top-color:var(--gold);}}
.ov-card.homeimprovement{{border-top-color:#7d6b3a;}}
.ov-card.medical{{border-top-color:var(--teal);}}
.ov-card.vehicles{{border-top-color:var(--blue);}}
.ov-card.workbenefits{{border-top-color:#4a6fa5;}}
.ov-card.journal{{border-top-color:var(--ink3);}}
.ov-icon{{font-size:20px;margin-bottom:8px;}}
.ov-title{{font-family:var(--serif);font-size:16px;font-weight:500;color:var(--ink);margin-bottom:4px;}}
.ov-count{{font-family:var(--mono);font-size:10px;color:var(--ink3);}}
.ov-preview{{margin-top:8px;font-size:11px;color:var(--ink3);line-height:1.5;}}
.add-tip{{margin-top:24px;padding:18px 20px;background:white;border:1px solid var(--rule);border-radius:3px;border-left:3px solid var(--gold);}}
.add-tip-label{{font-family:var(--mono);font-size:9px;color:var(--ink3);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;}}
.add-tip-cmd{{font-family:var(--mono);font-size:12px;color:var(--ink2);background:var(--bg2);padding:10px 12px;border-radius:2px;line-height:1.6;}}
::-webkit-scrollbar{{width:6px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:3px;}}
</style>
</head>
<body>
<div class="masthead">
  <div class="masthead-title">LifeLedger — Records</div>
  <div class="masthead-right">Phoenix, AZ · Updated {NOW} · {total_records} records</div>
</div>
<nav class="nav" id="nav"></nav>
<div class="summary-band">
  <div class="sum-cell"><div class="sum-label">Monthly saved</div><div class="sum-val gold">$49</div><div class="sum-sub">recurring negotiations</div></div>
  <div class="sum-cell"><div class="sum-label">One-time wins</div><div class="sum-val">$668</div><div class="sum-sub">returns · credits · DIY</div></div>
  <div class="sum-cell"><div class="sum-label">Total debt</div><div class="sum-val">$732k</div><div class="sum-sub">2 mortgages + student loan</div></div>
  <div class="sum-cell"><div class="sum-label">Records on file</div><div class="sum-val">{total_records}</div><div class="sum-sub">across {n_folders} folders</div></div>
</div>
<div class="layout">
<aside class="sidebar">
  <div class="sidebar-heading">Folders</div>
  {sidebar}
</aside>
<main class="content">
{content}
</main>
</div>
<script>
const sidebarItems = document.querySelectorAll('.sidebar-item');
const nav = document.getElementById('nav');
sidebarItems.forEach(item => {{
  const name = item.querySelector('.sidebar-item-name').textContent.trim();
  const oc   = item.getAttribute('onclick');
  const btn  = document.createElement('button');
  btn.className = 'nav-btn' + (item.classList.contains('active') ? ' active' : '');
  btn.textContent = name;
  btn.setAttribute('onclick', oc.replace('null,this)', 'this,null)'));
  nav.appendChild(btn);
}});
function toggleRecord(h) {{ h.closest('.record').classList.toggle('open'); }}
function showSection(id, navBtn, sidebarItem) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById('sec-' + id);
  if (sec) sec.classList.add('active');
  document.querySelectorAll('.nav-btn,.sidebar-item').forEach(el => el.classList.remove('active'));
  if (navBtn) navBtn.classList.add('active');
  if (sidebarItem) sidebarItem.classList.add('active');
  document.querySelectorAll('.sidebar-item').forEach(s => {{
    if ((s.getAttribute('onclick')||'').includes("'"+id+"'")) s.classList.add('active');
  }});
  document.querySelectorAll('.nav-btn').forEach(b => {{
    if ((b.getAttribute('onclick')||'').includes("'"+id+"'")) b.classList.add('active');
  }});
}}
</script>
</body>
</html>"""

# ── GIT + MAIN ─────────────────────────────────────────────────────────────────
def git(cmd):
    r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip() or r.stderr.strip()

if __name__ == "__main__":
    print(f"📋 Generating LifeLedger viewer — {NOW}")
    sidebar_items, sections, total = build_sections(FOLDERS)
    html = build_html(sidebar_items, sections, total)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"✅ Viewer written — {total} records across {len(FOLDERS)} folders")
    print("\n→ Publishing to GitHub Pages...")
    git(["git", "add", "-A"])
    ok, out = git(["git", "commit", "-m", f"Viewer refresh {NOW}"])
    if "nothing to commit" in out:
        print("   No changes — already up to date.")
    else:
        ok, out = git(["git", "push", "origin", "main"])
        print(f"   ✅ Live: https://the-daily-ops.github.io/lifeledger/lifeledger-viewer.html"
              if ok else f"   ⚠️  Push failed: {out}")
