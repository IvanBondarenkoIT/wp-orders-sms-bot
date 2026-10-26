# WP Orders → SMS bot

Telegram bot for DimKava: watches WooCommerce order notifications in a service group and sends a short customer SMS via the internal `sms-api-sender` connector.

This repo is **application-only**. Deploy to the alt server is done by the deploy hub (`catalog/*.yml`) — not from here.

## What it does

1. Long-polls Telegram.
2. Reacts only in `ALLOWED_CHAT_IDS` and only to messages from `DimKavaWPOrdersNotification_bot` (username and/or `SOURCE_BOT_USER_ID`).
3. Parses `order_id`, `order_date`, `total`, `phone`.
4. Sends SMS through `sms-api-sender` (`POST /api/v1/campaigns`, `utf: false`).
5. Replies in the same group: `sent` / `skip` / `fail`.

Idempotency: `campaign_id = wp-order-<order_id>` + SQLite `data/processed.db`.

## SMS template

```
DIM KAVA: Order #<order_id> received!
Date: <order_date>
Total: <total> GEL.
Our manager will call you shortly.
Contact us: https://ig.me/m/dimkava.georgia
```

## Environment

Copy `.env.example` → `.env`:

| Variable | Notes |
|----------|--------|
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `ALLOWED_CHAT_IDS` | CSV of group ids (negative) |
| `SOURCE_BOT_USERNAME` | Default `DimKavaWPOrdersNotification_bot` |
| `SOURCE_BOT_USER_ID` | Optional numeric id (preferred) |
| `SMS_API_URL` | Prod: `http://sms-api-sender:8000`; host: `http://127.0.0.1:8092` |
| `SMS_API_KEY` | Same key as `sms-api-sender` |
| `SMS_UTF` | `false` (ASCII, cheaper) |
| `DRY_RUN` | `true` locally → no SMS, reply `skip dry_run` |
| `IG_CONTACT_URL` | Instagram contact link |

## BotFather checklist

1. Create a bot → put token in `TELEGRAM_BOT_TOKEN`.
2. **Bot Settings → Group Privacy → Disable** (required to see other bots’ messages).
3. Add the bot to the orders group (same group as `DimKavaWPOrdersNotification_bot`).
4. Get group `chat_id` → `ALLOWED_CHAT_IDS`.
5. Preferably set `SOURCE_BOT_USER_ID` of the notification bot.

## Local run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env   # fill values; DRY_RUN=true for safe tests
pytest
python -m wp_orders_sms_bot.main
```

## Docker (prod shape)

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

- Network: external Docker network `edge` (resolves `sms-api-sender`).
- Volume: `./data` → SQLite.
- No published ports (long-poll only).
- `TZ=Asia/Tbilisi`, `restart: unless-stopped`.

## Example curl to sms-api-sender

From the alt host (or via SSH tunnel to `127.0.0.1:8092`):

```bash
curl -sS -X POST "http://127.0.0.1:8092/api/v1/campaigns" \
  -H "X-Api-Key: $SMS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "DIM KAVA: Order #9111 received!\nDate: 24 Oct 2026, 5:03 am\nTotal: 379 GEL.\nOur manager will call you shortly.\nContact us: https://ig.me/m/dimkava.georgia",
    "recipients": ["995599228754"],
    "utf": false,
    "campaign_id": "wp-order-9111"
  }'
```

Expected: HTTP `202` with `campaign_id` / `queued`. HTTP `409` → treat as already sent. HTTP `402` → insufficient balance.

From a sibling container on `edge`: `http://sms-api-sender:8000`.

## Deploy (hub)

Do **not** add `catalog/*.yml` in this repo. When the app is ready, tell the deploy hub chat «задеплой»:

1. Hub adds `catalog/wp-orders-sms-bot.yml` (compose build, network `edge`).
2. Secrets in hub `infra/wp-orders-sms-bot/.env`.
3. `python scripts/deploy_app.py wp-orders-sms-bot` + `test_app`.
4. Verify real order statuses in the group (`sent` / `skip` / `fail`) without leaking keys.

## Status replies (examples)

| Case | Reply |
|------|--------|
| Accepted (202) | `SMS sent for #9111 → 995***8754 (campaign wp-order-9111)` |
| Bad/missing phone | `SMS skip #9111: missing_phone` / `invalid_phone` |
| Parse failure | `SMS skip #…: parse_error` |
| Already processed | `SMS skip #9111: already_sent` |
| Balance | `SMS fail #9111: insufficient_balance` |
| Dry run | `SMS skip #9111: dry_run` |
