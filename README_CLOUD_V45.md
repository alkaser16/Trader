# GoldBot Cloud V4.5

Cloud version of GoldBot V4.4 for Render Web Service + Telegram webhook.

## Important
This bot is an analytical/alerting system. It does not execute trades and does not guarantee profitable or correct predictions.

## Deploy
1. Push this repository to GitHub.
2. Create a Render Web Service from the repository, or use the included `render.yaml` Blueprint.
3. Set the required environment variables in Render.
4. Deploy.
5. Copy the Render HTTPS URL into `PUBLIC_URL` and redeploy if it was not already set.
6. Open `/health` and confirm `{"status":"healthy"...}`.
7. Send `/start` to the Telegram bot.

## Required environment variables
- TWELVE_DATA_API_KEY
- TELEGRAM_BOT_TOKEN
- FINNHUB_API_KEY (optional for general/economic news; AUTO can fall back where supported)
- ADMIN_CHAT_IDS
- PUBLIC_URL
- WEBHOOK_SECRET

## Render
Build command:
`pip install -r requirements.txt`

Start command:
`gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT main:app`

Health check:
`/health`

The free Render web service is suitable for on-demand Telegram use, but it may sleep when inactive. A Telegram webhook request can wake the service; background monitoring is not guaranteed while the free instance is sleeping.

## Secrets
Never commit `.env` or real API keys/tokens to GitHub. Put secrets in Render Environment Variables.
