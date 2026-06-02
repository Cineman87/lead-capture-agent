# CLAUDE.md — Lead Capture Agent

## Project Overview

**Project name:** Lead Capture Agent
**What this agent does:** Serves a web contact form that saves submitted leads to a CSV file and sends an email notification to Mike via Gmail.
**What this agent does NOT do:** Does not score, qualify, or route leads; does not integrate with a CRM; does not send auto-replies to the person who submitted the form.
**Owner:** Mike
**Client:** Internal
**Status:** Active development

---

## Stack & Environment

**Language:** Python 3
**Key libraries:** flask, smtplib (stdlib)
**Entry point:** app.py
**Deployment:** Heroku (Procfile: `web: python app.py`)
**MCP servers in use:** None
**Agent Hermes involved:** No

---

## Core Rules

### 1. Ask, don't assume

If something is unclear about the task, architecture, or requirements — ask before writing a line of code. No silent guesses about intent.

### 2. Simplest solution first

Implement the minimum thing that works. No abstractions, refactors, or "improvements" that weren't requested.

### 3. Don't touch unrelated code

If a file isn't part of the current task, leave it alone. This is a maintained system, not a greenfield project.

### 4. Flag uncertainty explicitly

If you're not confident about something, say so before proceeding. Confidence without basis causes rework.

---

## Architecture Decisions

- Lead data is stored in `leads.csv` (flat file) — no database, keeps deployment simple on Heroku.
- Email notifications use Gmail SMTP SSL on port 465; password is read from the `SMTP_PASS` environment variable, never hardcoded.
- The form submits via `fetch` (AJAX) so the page doesn't reload — intentional UX choice.
- No rate limiting on `/submit` — assumed to be handled upstream or deemed acceptable for current volume.

---

## Off-Limits Files

- `.env` — environment variables, do not touch
- `leads.csv` — live lead data, do not modify or delete

---

## Known Issues & Workarounds

- `leads.csv` is committed to the repo as a seed/test file; in production it accumulates real lead data on the Heroku dyno (ephemeral storage — leads are lost on dyno restart unless a persistent store is added later).
- Email sending fails silently if `SMTP_PASS` is not set — this is intentional to avoid crashing the app on form submit.

---

## Testing

**How to run tests:** No automated tests yet. Test manually by running `python app.py` locally (with `SMTP_PASS` set if testing email) and submitting the form at `http://localhost:5000`.
**Before marking any task done:** Submit a test lead via the form, confirm it appears in `leads.csv`, and confirm the notification email arrives (or that the failure is logged gracefully).

---

## Client Context

**Client technical level:** Some technical
**Delivery format:** Web form accessible via Heroku URL; leads visible in `leads.csv` and via email notification
**Constraints to respect:** No external API calls beyond Gmail SMTP. Keep dependencies minimal — only `flask` in requirements.txt.

---

## Session Notes

Last worked on: 2026-06-02
Last change made: Moved SMTP password to environment variable (`SMTP_PASS`)
Next task: TBD
