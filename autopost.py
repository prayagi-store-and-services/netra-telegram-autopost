#!/usr/bin/env python3
"""Netra Ecosystem -> Telegram autoposter.

Watches, on a schedule:
  1. The Netra Ecosystem YouTube channel's official RSS feed (new public videos).
  2. GitHub Releases on the org's app repos (new app updates/versions).

New items are posted to the @Netraecosystem Telegram channel via @NetraEcosystemBot.
Links only - never video files or raw APK files. Downloads always point to the
app's page on the Netra Eco site.

State (already-announced item ids) lives in state/seen.json and is committed
back to this repo by the workflow. On the very first run the state is seeded
silently (no backlog flood) and, when a bot token is present, a single
"alerts are live" message is posted.

If TELEGRAM_BOT_TOKEN is absent the script runs in dry-run mode: it prints what
it would post and still records state, so enabling the token later never
re-posts a backlog.
"""
import json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET

ORG = "prayagi-store-and-services"
YT_CHANNEL_ID = "UCePc2TXpCV66xdG8Mzxzx3A"
YT_FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@Netraecosystem")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
GH_TOKEN = os.environ.get("GH_TOKEN", "").strip()
MAX_POSTS_PER_RUN = 3
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "seen.json")
APPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.json")

DRY_RUN = not TOKEN
log = lambda *a: print(*a, flush=True)


def http_get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "netra-telegram-autopost/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def gh_json(url):
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    return json.loads(http_get(url, headers))


def tg_send(text, button_text=None, button_url=None):
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    if button_text and button_url:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": button_text, "url": button_url}]]}
    if DRY_RUN:
        log("[dry-run] would post:\n" + text + (f"\n  [button: {button_text} -> {button_url}]" if button_url else ""))
        return True
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        log(f"[telegram] HTTP {e.code}: {e.read()[:300]!r}")
        return False
    if not res.get("ok"):
        log(f"[telegram] API error: {res}")
        return False
    log("[telegram] posted ok")
    return True


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_state():
    try:
        with open(STATE_PATH) as f:
            st = json.load(f)
    except Exception:
        st = {}
    st.setdefault("youtube", [])
    st.setdefault("releases", [])
    st.setdefault("seeded", False)
    return st


def save_state(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(st, f, indent=2)


def fetch_youtube():
    """Return list of dicts for the channel's recent videos."""
    try:
        raw = http_get(YT_FEED)
    except Exception as e:
        log(f"[youtube] feed fetch failed: {e}")
        return []
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        log(f"[youtube] feed parse failed: {e}")
        return []
    items = []
    for ent in root.findall("a:entry", ns):
        vid = (ent.findtext("yt:videoId", default="", namespaces=ns) or "").strip()
        title = (ent.findtext("a:title", default="", namespaces=ns) or "").strip()
        link_el = ent.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else (f"https://youtu.be/{vid}" if vid else "")
        pub = (ent.findtext("a:published", default="", namespaces=ns) or "").strip()
        if vid and title:
            items.append({"id": vid, "title": title, "link": link, "published": pub})
    log(f"[youtube] {len(items)} videos in feed")
    return items


def fetch_releases(apps):
    """Return list of dicts for recent releases across mapped app repos."""
    out = []
    try:
        repos = gh_json(f"https://api.github.com/orgs/{ORG}/repos?per_page=100&type=public")
    except Exception as e:
        log(f"[releases] repo list failed: {e}")
        return []
    names = {r["name"] for r in repos} if isinstance(repos, list) else set()
    for repo_name in sorted(set(apps) & names):
        try:
            rels = gh_json(f"https://api.github.com/repos/{ORG}/{repo_name}/releases?per_page=3")
        except Exception as e:
            log(f"[releases] {repo_name}: fetch failed: {e}")
            continue
        for rel in rels or []:
            out.append({
                "id": f"{repo_name}:{rel.get('id')}",
                "repo": repo_name,
                "tag": rel.get("tag_name", ""),
                "title": rel.get("name") or rel.get("tag_name", ""),
                "body": rel.get("body") or "",
                "url": rel.get("html_url", ""),
                "prerelease": bool(rel.get("prerelease")),
                "published": rel.get("published_at", ""),
            })
    log(f"[releases] {len(out)} recent releases across {len(set(apps) & names)} app repos")
    return out


def release_bullets(body, max_items=6, max_len=500):
    lines = [l.strip() for l in body.splitlines()]
    bullets, seen_hdr = [], False
    for l in lines:
        if not l:
            continue
        m = re.match(r"^[-*•]\s+(.*)", l)
        if m:
            bullets.append(m.group(1).strip())
        elif re.match(r"^#{1,6}\s", l):
            seen_hdr = True
        elif not seen_hdr and not bullets:
            continue  # skip intro prose before the first header/bullets
        elif len(bullets) < max_items:
            bullets.append(l.lstrip("# ").strip())
        if len(bullets) >= max_items:
            break
    if not bullets:
        bullets = [l for l in lines if l][:3]
    text = "\n".join(f"• {b}" for b in bullets[:max_items] if b)
    return text[:max_len]


def main():
    apps = json.load(open(APPS_PATH))
    st = load_state()
    new_posts = []

    yt_items = fetch_youtube()
    for it in reversed(yt_items):  # oldest first
        if it["id"] not in st["youtube"]:
            new_posts.append(("youtube", it))

    rel_items = fetch_releases(apps)
    for it in reversed(rel_items):
        if it["id"] not in st["releases"]:
            new_posts.append(("release", it))

    if not st["seeded"]:
        log(f"[init] first run: seeding state with {len(st['youtube']) + sum(1 for k,_ in new_posts if k=='youtube')} youtube ids and releases; no backlog posts")
        st["youtube"] = [i["id"] for i in yt_items]
        st["releases"] = [i["id"] for i in rel_items]
        st["seeded"] = True
        save_state(st)
        if not DRY_RUN:
            tg_send("🪷 <b>Netra Ecosystem alerts are now automatic</b>\n\nNew app updates and new YouTube videos will be posted here automatically. Stay tuned!")
        return

    posted = 0
    for kind, it in new_posts:
        if posted >= MAX_POSTS_PER_RUN:
            log(f"[limit] max posts per run reached; remaining items stay pending (state not updated for them)")
            break
        if kind == "youtube":
            ok = tg_send(
                f"🪷 <b>New video on Netra Ecosystem YouTube</b>\n\n<b>{esc(it['title'])}</b>\n\n▶️ Watch: {it['link']}",
                "▶️ Watch on YouTube", it["link"])
            if ok:
                st["youtube"].append(it["id"]); posted += 1
        else:
            app = apps.get(it["repo"], {"name": it["repo"], "page": f"https://github.com/{ORG}/{it['repo']}/releases"})
            pre = " (beta)" if it["prerelease"] else ""
            body = release_bullets(it["body"])
            text = f"🪷 <b>{esc(app['name'])} {esc(it['tag'])}{pre}</b>\n"
            if body:
                text += f"\n{esc(body)}\n"
            text += f"\n⬇️ Download: {app['page']}"
            ok = tg_send(text, "⬇️ Download", app["page"])
            if ok:
                st["releases"].append(it["id"]); posted += 1
        time.sleep(2)

    # keep state lists bounded
    st["youtube"] = st["youtube"][-200:]
    st["releases"] = st["releases"][-500:]
    save_state(st)
    log(f"[done] posted={posted} dry_run={DRY_RUN}")


if __name__ == "__main__":
    main()
