# Daily Idea Bot

## Project Overview

Telegram bot that scrapes tech trends from Twitter/X and GitHub, then generates creative project ideas using Gemini AI. The topic is configurable via `IDEA_TOPIC` env var.

## Tech Stack

- **Language**: Python 3.11+
- **Telegram**: python-telegram-bot 21+
- **AI**: Google Gemini 2.0 Flash (google-genai)
- **HTTP**: httpx (async)
- **Scheduler**: APScheduler (cron-based)
- **Validation**: Pydantic v2
- **Env**: python-dotenv
- **Lint**: ruff

## Architecture

```
main.py (DailyIdeaService)  — orchestrates everything
  ├── scraper.py (TrendScraper)  — collects trends from Twitter/X + GitHub
  ├── analyzer.py (TrendAnalyzer) — Gemini prompt → AnalysisResult (Pydantic)
  └── bot.py (IdeaBot)           — Telegram handlers + message formatting
```

### Flow

1. Trigger: cron schedule OR `/idea` command
2. `TrendScraper.get_all_trends()` — runs all enabled scrapers concurrently
3. `TrendAnalyzer.analyze_and_generate(trends)` — sends to Gemini, parses JSON response
4. `IdeaBot.send_ideas()` — formats and sends to Telegram

### Scraper Plugin System

- All scrapers inherit `BaseScraper` with `name`, `requires_sela`, `fetch()` method
- Registered in `AVAILABLE_SCRAPERS` dict
- Enabled via `ENABLED_SCRAPERS` env var (comma-separated)
- Twitter requires Sela Net API key; GitHub uses free API

## Key Environment Variables

- `TELEGRAM_BOT_TOKEN` — Telegram bot token (required)
- `TELEGRAM_CHAT_ID` — Target chat ID (required)
- `GEMINI_API_KEY` — Google Gemini API key (required)
- `SELA_API_KEY` — Sela Net API key (required for Twitter)
- `IDEA_TOPIC` — Idea generation topic, e.g. "AI agent", "SaaS" (default: "AI agent")
- `ENABLED_SCRAPERS` — Comma-separated scraper names (default: "twitter,github")
- `DAILY_SCHEDULE_TIME` — Cron time in HH:MM format (default: "09:00")
- `TWITTER_QUERIES` — Comma-separated Twitter search queries

## Commands

```bash
# Run
python -m src.main

# Lint
ruff check src/

# Test
pytest
```

## Conventions

- Async throughout (httpx, telegram, Gemini)
- Pydantic models for structured data (TrendItem, IdeaSuggestion, AnalysisResult)
- Gemini configured with `response_mime_type="application/json"` for reliable JSON output
- Bot uses `drop_pending_updates=True` to ignore stale messages on restart
