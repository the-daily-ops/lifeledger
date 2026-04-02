# LifeLedger Cheat Sheet
*Last updated: March 30, 2026*

---

## 🌐 Live URLs
| Page | URL |
|---|---|
| **Task Board** | `https://the-daily-ops.github.io/lifeledger/dashboard.html` |
| **Records Viewer** | `https://the-daily-ops.github.io/lifeledger/lifeledger-viewer.html` |

> Bookmark both on your phones. Auto-refreshes every 5 minutes.

---

## 🔄 Dashboard Commands
| Action | Command |
|---|---|
| **Regenerate + publish** | `dashboard` (alias) or see full path below |
| Full path if alias fails | `python3 "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/generate-dashboard.py"` |
| Check scheduler status | `launchctl list \| grep lifeledger` |
| Stop scheduler | `launchctl unload ~/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist` |
| Restart scheduler | `launchctl load ~/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist` |
| View scheduler log | `cat "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/dashboard-scheduler.log"` |
| View error log | `cat "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/dashboard-scheduler-error.log"` |

> Dashboard reads vault + Honey list → writes dashboard.html → pushes to GitHub → Netlify deploys in seconds.
> **Don't say "update the dashboard" to Claude** — the Python script handles it automatically.

---

## 👀 Watcher Commands
| Action | Command |
|---|---|
| Start watcher | `bash "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/start-watcher.sh"` |
| Or use alias | `lifeled` |
| Stop watcher | `pkill -f start-watcher.sh` |
| Restart watcher | `pkill -f start-watcher.sh && bash "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/start-watcher.sh"` |

> Watcher polls every 5 seconds. On vault change: moves completed tasks → sorts Drop List → backs up vault.

---

## 💾 Version Control & Backup
Three layers of backup are always running:

| Layer | What's backed up | How often | Where |
|---|---|---|---|
| **Vault git** | `2026-02-25.md` + all vault files | Every watcher cycle (5 sec) | Local git history in vault folder |
| **LifeLedger GitHub** | All records, scripts, HTML files | Every `dashboard` run | `github.com/the-daily-ops/lifeledger` |
| **iCloud** | Everything in iCloud Drive | Continuously | Apple's servers |

### 🔁 How to restore the vault after accidental overwrite:
```bash
cd "/Users/coto/Library/Mobile Documents/iCloud~md~obsidian/Documents/Digital Bullet Journal"
git log --oneline                                          # see all snapshots
git checkout HEAD~1 -- "01 Daily/2026-02-25.md"           # restore 1 version back
git checkout HEAD~3 -- "01 Daily/2026-02-25.md"           # restore 3 versions back
```

### 💾 Manual vault backup anytime:
```bash
bash "/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/vault-backup.sh"
```

---

## 📱 Wife's List
| Action | How |
|---|---|
| Her file location | `/Users/coto/Library/Mobile Documents/com~apple~CloudDocs/Honey To Do List.md` |
| Auto-syncs to dashboard | Every 5 minutes via scheduler (no action needed) |
| Import to your vault | Say "read the Honey To Do List" to Claude |
| For events to show on calendar | She uses `- EventName` under her Events section |
| For tasks to show in wife banner | She uses `- [ ] Task name` format |

---

## 🤖 Claude Prompts
| Say this | What happens |
|---|---|
| `Boot LifeLedger` | Reads all 3 context files, confirms ready |
| `Read the Honey To Do List` | Reads her file, imports new items to vault |
| `What should I focus on today?` | Daily briefing from vault |
| `Log [task] as complete` | Moves to ✅ Completed, creates LifeLedger record |
| `Add [item] to the vault` | Adds task to correct section |
| `Update the viewer` | Re-syncs lifeledger-viewer.html with latest records |
| `Add [date] to dates and events` | Adds event to 📅 section so it shows on calendar |
| `Read my CostSavings folder` | Shows savings summary |

---

## 🗂️ LifeLedger Folder Guide
| Folder | What goes there |
|---|---|
| `CostSavings/` | Bill negotiations, subscription cancellations |
| `Medical/` | Appointments, records, insurance |
| `WorkBenefits/` | HSA, 401K, PTO, open enrollment |
| `Finances/` | Budget, investments, loans |
| `HomeImprovement/` | Projects, contractors, warranties |
| `Journal/` | Misc completed life events |
| `Analytics/` | Savings summaries, trend reports |
| `Content/` | Blog drafts, YouTube scripts |

**File naming:** `YYYY-MM-DD-Description.md` · Example: `2026-03-25-Cox-Negotiation.md`

---

## 📁 Key File Locations
| File | Path |
|---|---|
| Main task file | `.../Digital Bullet Journal/01 Daily/2026-02-25.md` |
| Wife's honey list | `~/Library/Mobile Documents/com~apple~CloudDocs/Honey To Do List.md` |
| LifeLedger folder | `~/Library/Mobile Documents/com~apple~CloudDocs/LifeLedger/` |
| Dashboard generator | `...LifeLedger/generate-dashboard.py` |
| Vault backup script | `...LifeLedger/vault-backup.sh` |
| Scheduler plist (active) | `~/Library/LaunchAgents/com.coto.lifeledger.dashboard.plist` |
| MCP config | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| GitHub repo | `github.com/the-daily-ops/lifeledger` |

---

## 📜 Scripts in LifeLedger/
| Script | Purpose |
|---|---|
| `generate-dashboard.py` | Rebuilds dashboard.html + pushes to GitHub (run anytime) |
| `run-dashboard.sh` | Shell wrapper called by launchd scheduler |
| `start-watcher.sh` | Watches vault, sorts Drop List, backs up on every change |
| `vault-backup.sh` | Commits vault to git — run manually or auto via watcher |
| `obsidian-maintenance.sh` | Moves [x] completed tasks to ✅ section |
| `sort-drop-list.sh` | AI-powered Drop List → correct section sorter |
| `install-scheduler.sh` | One-time scheduler install (already done) |

---

## 💰 Next Negotiation Targets
1. Phone bill — Voss tactics, call retention dept
2. Car insurance — shop and compare first
3. Apple subscriptions — Settings → Subscriptions
4. APS time-of-use plan
5. Medical bills — always negotiable
