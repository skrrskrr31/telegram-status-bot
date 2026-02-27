"""
TELEGRAM STATUS BOT
Her 5 dakikada GitHub Actions tarafından çalıştırılır.
Son 7 dakikada /durum veya /hata komutu geldiyse cevap verir.
"""
import os, json, base64, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

BOTS = {
    "purdyblog": "skrrskrr31/purdyblog_bot",
    "flaq_quiz": "skrrskrr31/flaq_quiz_bot",
    "mindset":   "skrrskrr31/mindset-forge-bot",
}


def tg_send(text):
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data
    )
    urllib.request.urlopen(req, timeout=10)


def tg_get_updates():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=3"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read()).get("result", [])


def gh_read_json(repo, path):
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "telegram-status-bot"
    }
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return json.loads(base64.b64decode(data["content"]).decode())
    except:
        return None


def handle_durum():
    lines = ["📊 <b>Bot Durumu</b> (son 10 çalışma)\n"]
    for bot_name, repo in BOTS.items():
        log = gh_read_json(repo, "run_log.json")
        if not log or not log.get("runs"):
            lines.append(f"<b>{bot_name}</b>: henüz log yok\n")
            continue
        runs = log["runs"][-10:]
        ok  = sum(1 for r in runs if r["status"] == "ok")
        err = sum(1 for r in runs if r["status"] == "error")
        last = runs[-1]
        icon = "✅" if last["status"] == "ok" else "❌"
        ts   = last["ts"].replace("T", " ")
        lines.append(f"{icon} <b>{bot_name}</b>: {ok}✅ {err}❌  |  son: {ts}")
    tg_send("\n".join(lines))


def handle_hata():
    all_errors = []
    for bot_name, repo in BOTS.items():
        log = gh_read_json(repo, "run_log.json")
        if not log:
            continue
        for r in log["runs"]:
            if r["status"] == "error":
                all_errors.append((r["ts"], bot_name, r.get("error", "bilinmeyen hata")))

    if not all_errors:
        tg_send("✅ Son çalışmalarda hiç hata yok!")
        return

    all_errors.sort(reverse=True)
    lines = ["❌ <b>Son Hatalar</b>\n"]
    for ts, bot, err in all_errors[:5]:
        lines.append(f"<b>{bot}</b>  [{ts.replace('T', ' ')}]\n<code>{err}</code>\n")
    tg_send("\n".join(lines))


# ── Son 7 dakikadaki komutları işle ──────────────────────────
now    = datetime.now(timezone.utc)
cutoff = now - timedelta(minutes=7)

updates = tg_get_updates()
handled = set()

for u in sorted(updates, key=lambda x: x.get("update_id", 0)):
    msg      = u.get("message", {})
    msg_time = datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc)
    text     = msg.get("text", "").strip().lower()

    if msg_time < cutoff:
        continue
    if text in handled:
        continue

    if "/durum" in text:
        print(f"[CMD] /durum alindi ({msg_time})")
        handle_durum()
        handled.add(text)
    elif "/hata" in text:
        print(f"[CMD] /hata alindi ({msg_time})")
        handle_hata()
        handled.add(text)

if not handled:
    print("Yeni komut yok.")
