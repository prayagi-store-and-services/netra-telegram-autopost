# ATIF v3.0 - applicable parts for netra-telegram-autopost

ATIF v3.0 (Absolute Truth & Intelligence Framework) is the owner's permanent master rule, issued 9 Nov 2026. Canonical full text: private governance copy (`netra-intruder`, `docs/ATIF-v3.0.md`). This file lists only the parts that apply to THIS automation.

## Applicable parts and why

- Part 01, 02: channel posts must announce only real events.
- Part 06: no invented updates, versions or videos; `state/seen.json` is the honest record of what was announced.
- Part 09: posts are built from the live GitHub Releases API and the official YouTube RSS feed at run time.
- Part 14: the ~15-minute schedule can be delayed by GitHub Actions; this is stated.
- Part 20: Download buttons link to the app's Eco site page, never a raw APK or invented URL.

## Data this automation publishes, and its status

- App update posts: real GitHub Releases on org repos listed in `apps.json` - VERIFIED source.
- YouTube posts: the official channel RSS feed; video files are never uploaded.
- First run seeds memory silently to avoid backlog floods - disclosed behaviour.

## Standing rule

A post goes out only when its source event exists. A failed or partial feed produces no speculative post.

## Source labels (owner-approved 9 Nov 2026)

Every user-visible data claim carries a short source label. UI strings stay short; the label for each claim lives in this file's "Data this app shows" list and in WHATS_NEW/release notes (e.g. "Source: Android BatteryManager"). In-app visible source labels are planned and ship only after the owner's UI preview.

## Stale data: OLD marking (owner-approved 9 Nov 2026)

Any dated or versioned claim that stops matching reality is marked "OLD (as of <date>)" at the next check and corrected in the same or a following PR. Stale claims are never silently edited and never left unmarked.

## Weekly audit (owner-approved 9 Nov 2026)

A weekly audit records each material claim as VERIFIED or NOT VERIFIED in `docs/ATIF-AUDIT.md`, newest first. Failures and NOT VERIFIED items are listed first in every audit and every report.
