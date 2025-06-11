# Raspberry Pi Multi-Agent Trading Desk

This repository contains a containerized, multi-agent trading system designed to run on a Raspberry Pi (or any Docker host). It trades via **Alpaca (paper)**, communicates through **Redis Streams**, plans with **GPT‑4o‑mini‑high**, stores memory in **Weaviate**, and chats through **Telegram**.

## Quick‑start

```bash
# 1. Clone & enter
git clone <repo-url>
cd trading-firm

# 2. Fill credentials
cp .env.example .env
nano .env            # edit tokens
nano config/settings.yaml  # edit feeds & risk

# 3. Boot the desk
docker compose up --build -d
```

## Telegram Bot Commands

| Command | Function |
|---------|----------|
| `/status` | Show RUN/HALT |
| `/pause`  | Set HALT flag |
| `/resume` | Clear HALT flag |
| `/objectives` | Weekly OKRs |
| `/tasks` | Current tasks |
| `/next_events` | Upcoming catalysts |
