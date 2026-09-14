# Render entrypoint: the Flask app handles Telegram webhooks.
from cloud_app import app

__all__ = ["app"]
