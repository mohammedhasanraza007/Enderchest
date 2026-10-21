# OWNER_TASKS.md — What only you can do, and when

> **Read when:** starting a phase (look up its row) or when Claude says "BLOCKED". Claude cannot photograph your belongings, press your webcam shutter, print on your printer, hold your Gemini key or judge how something looks to you. Claude must never fake any of these (`CLAUDE.md` 8).

## Once, before Phase 0
- Windows 10 or 11 with **Docker Desktop** (WSL2 backend on), **Git for Windows**, **Claude Code**, Chrome or Edge. No Python or Node needed.
- Unzip the latest zip into `C:\Projects\` (it creates `C:\Projects\Enderchest`). Do **not** run `git init`: the zip already holds the git history.
- Once: create one Claude project for Enderchest and paste this into its instructions (D-071): "When an attached zip is named `pack-*.zip` or `phase*.zip`, do not ask first. Unzip it into a new worktree folder and follow CLAUDE.md section 0 inside it, starting at once." Without a project, use the fallback line in "Every chat" below.
- Start Claude Code, run `/permissions`, check the deny list shows `Bash(...)` and `PowerShell(...)` Docker rules; run `/model` and choose Sonnet 5.5.

## Every chat (zip workflow, D-067, D-071)
- Paste the latest zip into a new chat in the Enderchest project. Claude starts by itself: nothing to type and no confirmation step.
- Claude checks the visuals, writes a RESUME block and a short brief, builds, and ends with a zip (for example `phase0.zip`) and a short message.
- Optional: add a line with acceptance results, Docker output or hand edits. Name any file you changed by hand; otherwise the change is not in the zip and is lost.
- Acceptance runs and Docker probes happen on your laptop, from the latest zip. Their results go in your next message.
- Answer owner-only questions in one batch in that message.
- If a chat does not start by itself, the project instruction is missing. Paste this line instead: *Read the attached zip: unzip it to a new worktree and follow CLAUDE.md section 0 exactly.*
- Then run `/clear` or open a new chat in the project, and paste the new zip.

## By phase
| Phase | You provide | How long |
|---|---|---|
| 0 | Run the 3-minute acceptance script (end of the spec). Say "accepted" | 3 min |
| 1 | Approve the shell screenshot; complete the welcome screen | 3 min |
| 2 | Real-webcam add, print one label on paper, scan it back, Trash test | 5 min |
| 3 | **20 photos + `labels.csv` confirmed** (`tests/fixtures/README.md`); optional Gemini key (Google AI Studio) | 30–45 min |
| 4 | Create a due task and an expiring item; allow browser notifications | 3 min |
| 5 | Compare the dashboard with the reference; approve | 3 min |
| 6 | **10 owned + 10 not-owned photos**; paste-check two products | 20 min + 5 min |
| 7 | Live webcam check of the coach | 5 min |
| 8 | Approve light mode and the truck (or defer in writing) | 10 min |
| 9 | Gemini key | 2 min |

## Always
- Keep the backup folder (`%USERPROFILE%\Enderchest-Backups`) out of cleanup tools. It is your safety net if Docker Desktop is ever reset.
- Reminders show while an Enderchest tab is open; leave it pinned if you want browser notifications.
- To save Claude Pro usage: one phase per chat, `/clear` between chats, and let the zip carry the memory (`CLAUDE.md` section 0).
