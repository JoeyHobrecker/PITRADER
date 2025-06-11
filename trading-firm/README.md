# Raspberry Pi Multi-Agent Trading Desk

This repository contains a containerized, multi-agent trading system designed to run on a resource-constrained device like a Raspberry Pi. It uses advanced AI/ML models for strategic planning, real-time signal generation, and risk management.

## Core Technologies

- **Trading:** Alpaca (Paper Trading)
- **Messaging:** Redis Streams
- **Reasoning:** OpenAI GPT-4 Series
- **Memory:** Weaviate Vector Store
- **I/O:** Telegram Bot

## Architecture

The system is composed of several independent agents communicating via a central message bus (Redis Streams). This decoupled design allows for resilience and scalability.

```mermaid
graph TD
    subgraph User
        TelegramBot[<B>telegram_bot</B>]
    end

    subgraph "AI Planners (Cron)"
        Chief[<B>chief_strategist</B>]
        Legal[<B>legal_sentinel</B>]
        Macro[<B>macro_calendar</B>]
    end

    subgraph "Real-time Agents"
        NewsMiner[<B>news_miner</B>]
        SignalMaker[<B>signal_maker</B>]
        Trader[<B>trader</B>]
        Watchdog[<B>watchdog</B>]
    end

    subgraph "Data & State"
        Memory[<B>memory_keeper</B> <br/>(Weaviate Client)]
        Weaviate[(Weaviate Cloud)]
        Redis[(Redis Streams)]
        Alpaca[(Alpaca API)]
    end

    %% Message Flows
    User -- /commands --> TelegramBot
    TelegramBot -- queries --> Memory
    TelegramBot -- HALT/RESUME --> Redis

    Chief -- publishes --> Redis(playbook)
    Legal -- publishes --> Redis(playbook)
    Macro -- publishes --> Redis(playbook)
    Chief & Legal & Macro -- store/query --> Memory

    NewsMiner -- publishes --> Redis(news_raw)
    NewsMiner -- publishes headlines --> Redis(playbook)

    Redis(news_raw) --> SignalMaker
    Redis(playbook) --> SignalMaker

    SignalMaker -- publishes --> Redis(trade_signals)
    Redis(trade_signals) --> Trader
    Trader -- places orders --> Alpaca
    Alpaca -- provides fills --> Trader
    Trader -- publishes --> Redis(fills)

    Redis(fills) --> Watchdog
    Watchdog -- on breach --> Redis(playbook)

    Memory -- interacts with --> Weaviate
```

## Setup & Deployment

Designed for a one-command bootstrap on a Raspberry Pi (or any machine with Docker).

### Install Docker & Docker Compose
Follow the official guides for your OS/architecture.

### Configure Credentials
Copy the example environment file and edit it with your actual API keys and tokens.

```bash
cp .env.example .env
nano .env # Or your favorite editor
```

You also must edit `config/settings.yaml` to configure RSS feeds and other parameters.

### Launch
Build and run all services in the background.

```bash
docker compose up --build -d
```

### Telegram Bot Commands
/start - Welcome message.
/status - Check if the system is running or halted.
/pause - Immediately halt all new trading activity.
/resume - Resume trading activity.
/objectives - Show the current high-level objectives from the weekly playbook.
/tasks - Show the specific, actionable tasks from the weekly playbook.
/next_events - List upcoming catalyst events (e.g., CPI, court dates).
