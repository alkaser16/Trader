import os
import threading
from flask import Flask, jsonify, request

from config import TELEGRAM_BOT_TOKEN, REQUEST_TIMEOUT
from bot.telegram import process_update, telegram_request, send_message
from monitor import start as start_monitor

app = Flask(__name__)

PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

_monitor_started = False
_monitor_lock = threading.Lock()


def _start_monitor_once():
    global _monitor_started
    with _monitor_lock:
        if not _monitor_started:
            start_monitor(send_message)
            _monitor_started = True


def configure_webhook():
    if not PUBLIC_URL:
        print("WARNING: PUBLIC_URL is not set; Telegram webhook was not configured.")
        return
    url = f"{PUBLIC_URL}/telegram/webhook"
    payload = {"url": url, "drop_pending_updates": False}
    if WEBHOOK_SECRET:
        payload["secret_token"] = WEBHOOK_SECRET
    try:
        result = telegram_request("setWebhook", payload)
        print("Telegram webhook configured:", url)
        print(result.get("description", "OK"))
    except Exception as exc:
        print("WARNING: Could not configure Telegram webhook:", exc)


@app.get("/")
def home():
    return jsonify({
        "service": "GoldBot Cloud V4.5",
        "status": "ok",
        "telegram": "webhook",
    })


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "service": "goldbot-v4.5"})


@app.post("/telegram/webhook")
def telegram_webhook():
    if WEBHOOK_SECRET:
        received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if received != WEBHOOK_SECRET:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

    update = request.get_json(silent=True)
    if not isinstance(update, dict):
        return jsonify({"ok": False, "error": "invalid update"}), 400

    try:
        process_update(update)
        return jsonify({"ok": True})
    except Exception as exc:
        print("Webhook update error:", exc)
        return jsonify({"ok": False}), 500


@app.post("/admin/webhook/set")
def set_webhook():
    # Optional manual endpoint. Protect it with WEBHOOK_SECRET.
    if WEBHOOK_SECRET:
        received = request.headers.get("X-Admin-Secret", "")
        if received != WEBHOOK_SECRET:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
    configure_webhook()
    return jsonify({"ok": True, "public_url": PUBLIC_URL})


_start_monitor_once()
configure_webhook()
