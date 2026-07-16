# Block 2.4 — Operationalize the recall-watch cron

> **Model**: Haiku 5 · **Thinking**: Medium · **Stage**: 2 (Measurement & Growth) · **Status**: ⬜ Not started
> **Parent**: [`../imp_part_2.md`](../imp_part_2.md) §2.4

---

## TL;DR

`backend/scripts/recall_watch_cron.py` is fully implemented (walks every saved vehicle, checks NHTSA for open recalls, emails owners) but **nothing schedules it**. Add a macOS `launchd` plist + Makefile targets to install/uninstall/test it, and document the commands.

**Do NOT use GitHub Actions** — the accounts DB (`data/rapp.db`) lives on local disk on the Mac that runs the backend; a GitHub-hosted runner can't reach it. `launchd` (or a user crontab) on that same host is the correct mechanism.

---

## Context you need

- The script is invoked as `uv run python -m backend.scripts.recall_watch_cron` (module path `backend.scripts.recall_watch_cron`, confirmed). Its docstring already says "Run manually" / "Schedule daily via cron/launchd" — this block provides that scheduling.
- It's idempotent and dedup'd (`DbRecallAlertSent` per VIN/campaign), so running it repeatedly is safe.
- The root `Makefile` exists and has a `backup-db:` target (line 75) as precedent for adding ops targets.

---

## ⚠️ Corrections vs. `imp_part_2.md`

None. The module path, the "run manually" docstring, and the Makefile-with-`backup-db` precedent are all accurate. The `/path/to/RAPP` placeholder in the plist is intentional and is substituted at install time by the Makefile target (below) — do not hardcode this machine's path.

---

## Change 1 — Create `scripts/com.rapp.recall-watch.plist`

Create the file exactly as below. The literal `/path/to/RAPP` is a placeholder the Makefile substitutes with `$(pwd)` at install time (keeps it portable across machines):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rapp.recall-watch</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-lc</string>
        <string>cd /path/to/RAPP &amp;&amp; uv run python -m backend.scripts.recall_watch_cron</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/rapp-recall-watch.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/rapp-recall-watch.log</string>
</dict>
</plist>
```

---

## Change 2 — Add Makefile targets (root `Makefile`, near the `backup-db:` target)

Add these three targets. **Makefile recipes must be tab-indented, not spaces** — verify with `cat -A Makefile | grep recall` (recipe lines must start with `^I`):
```makefile
recall-watch-install:
	@echo "Installing recall-watch daily cron (8am) via launchd..."
	sed "s|/path/to/RAPP|$(shell pwd)|g" scripts/com.rapp.recall-watch.plist > ~/Library/LaunchAgents/com.rapp.recall-watch.plist
	launchctl load ~/Library/LaunchAgents/com.rapp.recall-watch.plist
	@echo "Installed. Logs at /tmp/rapp-recall-watch.log"

recall-watch-uninstall:
	launchctl unload ~/Library/LaunchAgents/com.rapp.recall-watch.plist || true
	rm -f ~/Library/LaunchAgents/com.rapp.recall-watch.plist

recall-watch-once:
	uv run python -m backend.scripts.recall_watch_cron
```
> Also add the three target names to the `.PHONY:` line if the Makefile has one (grep for `.PHONY`).

---

## Change 3 — Document the commands

Add a short entry to `CLAUDE.md`'s **Commands** section (near the existing `make backup-db` mention):
```md
# Recall-watch daily cron (macOS launchd, host with the accounts DB)
make recall-watch-once       # run one pass immediately (test)
make recall-watch-install    # schedule daily at 8am
make recall-watch-uninstall  # remove the schedule
```

---

## Do NOT touch

- `backend/scripts/recall_watch_cron.py` — it's complete; you're scheduling it, not editing it.
- Do not add a GitHub Actions workflow for this (see TL;DR).
- Do not hardcode this dev machine's absolute path into the committed plist — leave the `/path/to/RAPP` placeholder.

---

## Verification

1. **One-shot run works** — with at least one saved repair for a vehicle with a known open NHTSA recall (pick any real VIN/model-year with a currently-open recall):
   ```bash
   make recall-watch-once
   ```
   Confirm the log shows a recall lookup and an email attempt (or, with no Resend key, a `recall_watch_email_send_failed`/dev log line — the point is the code path runs).
2. **Install registers the job**:
   ```bash
   make recall-watch-install
   launchctl list | grep rapp
   ```
   Must show `com.rapp.recall-watch`. The installed plist at `~/Library/LaunchAgents/com.rapp.recall-watch.plist` should have the real absolute path substituted (no `/path/to/RAPP` left).
3. **Uninstall cleans up**:
   ```bash
   make recall-watch-uninstall
   launchctl list | grep rapp   # returns nothing
   ```
4. Backend lint/type still clean (only if you touched any `.py`, which this block does not): `uv run ruff check backend/`.

---

## Definition of Done

- [ ] `scripts/com.rapp.recall-watch.plist` created (with `/path/to/RAPP` placeholder)
- [ ] `recall-watch-install` / `-uninstall` / `-once` Makefile targets added (tab-indented; `.PHONY` updated if present)
- [ ] Commands documented in `CLAUDE.md`
- [ ] `make recall-watch-once` runs; `make recall-watch-install` registers via `launchctl list | grep rapp`; uninstall removes it
- [ ] Committed: `feat(ops): Block 2.4 schedule recall-watch via launchd + make targets`
- [ ] `imp_part_2.md` §1 tracker row 2.4 → `✅ Done`; session logged in §5
