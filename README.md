# netra-telegram-autopost

Free, self-hosted automation that posts Netra Ecosystem updates to the
[@Netraecosystem](https://t.me/Netraecosystem) Telegram channel via
@NetraEcosystemBot.

Watches, every ~15 minutes (GitHub Actions schedule; delays possible):

1. **YouTube** - the Netra Ecosystem channel's official RSS feed. New public
   videos are posted as title + watch link. Video files are never uploaded.
2. **App updates** - GitHub Releases on the org's app repos (see `apps.json`).
   New versions are posted as app banner name + version, changelog bullets and
   a Download button linking to the app's page on the Netra Eco site - never a
   raw APK link.

First run seeds its memory silently (no backlog flood) and posts one
"alerts are live" message. `state/seen.json` tracks announced items and is
committed back by the workflow.

Secrets: `TELEGRAM_BOT_TOKEN` (repo secret). Everything else is public data.
