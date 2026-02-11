# Daily Idea Bot

AI agent that searches X (Twitter) for trending keywords in your interest area and generates daily project ideas via Telegram using Gemini AI.

Collects real-time trends based on configurable search queries, analyzes them with AI, and delivers actionable 1-day MVP ideas every morning.

## Features

- **Keyword-based Trend Search**: Searches X (Twitter) for trending content based on your custom queries
- **Configurable Topic**: Set `IDEA_TOPIC` to any theme (AI agent, SaaS, Chrome extension, CLI tool, etc.)
- **AI-powered Analysis**: Gemini 2.0 Flash analyzes trends and generates creative project ideas
- **Daily Schedule**: Auto-sends ideas at your configured time via Telegram
- **On-demand**: `/idea` command for instant idea generation
- **Extensible Scrapers**: Plugin architecture — GitHub trending is included as an optional source, and you can add any search platform by extending `BaseScraper`

## Prerequisites

- Python 3.11+

## Quick Start

### 1. Install

```bash
git clone https://github.com/hdain/daily-idea-bot.git
cd daily-idea-bot

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Sela Net (for Twitter/X scraping)
SELA_API_KEY=your_sela_api_key

# Idea topic (e.g., "AI agent", "SaaS", "Chrome extension", "CLI tool")
IDEA_TOPIC=AI agent

# Schedule (24h format, e.g., "09:00")
DAILY_SCHEDULE_TIME=09:00

# Enabled scrapers (comma-separated)
# Available: twitter, github
ENABLED_SCRAPERS=twitter,github

# Twitter search queries (comma-separated)
TWITTER_QUERIES=AI agent,developer tools,tech meme,viral app
```

### 3. Run

```bash
python -m src.main
```

## Topic Examples

Change `IDEA_TOPIC` to get ideas for any theme:

```env
IDEA_TOPIC=AI agent           # AI agent project ideas
IDEA_TOPIC=SaaS               # SaaS product ideas
IDEA_TOPIC=Chrome extension   # Browser extension ideas
IDEA_TOPIC=CLI tool           # Command-line tool ideas
IDEA_TOPIC=mobile app         # Mobile app ideas
```

## API Keys

| Service | Link | Purpose |
|---------|------|---------|
| Telegram Bot | [@BotFather](https://t.me/BotFather) | Bot token |
| Gemini | [Google AI Studio](https://aistudio.google.com/) | AI analysis |
| Sela Net | [selanet.ai](https://www.selanet.ai/) | Twitter/X scraping |

### Finding your Telegram Chat ID

1. Send any message to your bot
2. Open `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in the response

## Data Sources

| Source | Sela Required | Description |
|--------|---------------|-------------|
| `twitter` | Yes | Twitter/X trends via Sela Net API |
| `github` | No | Trending repositories (free GitHub API) |

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/idea` | Generate ideas now |
| `/status` | Bot status |
| `/help` | Help |

## Adding a New Data Source

1. Create a scraper class in `src/scraper.py`:

```python
class MyNewScraper(BaseScraper):
    name = "MySource"
    requires_sela = False

    async def fetch(self) -> list[TrendItem]:
        # Your implementation
        ...
```

2. Register it:

```python
AVAILABLE_SCRAPERS["mysource"] = MyNewScraper
```

3. Enable in `.env`:

```env
ENABLED_SCRAPERS=twitter,github,mysource
```

## Project Structure

```
daily-idea-bot/
├── pyproject.toml      # Dependencies
├── .env.example        # Environment template
├── .gitignore
├── LICENSE             # MIT License
├── CLAUDE.md           # AI assistant context
├── README.md
└── src/
    ├── __init__.py
    ├── main.py         # Entry point, scheduler, service orchestration
    ├── bot.py          # Telegram bot handlers and message formatting
    ├── scraper.py      # Trend scrapers (plugin architecture)
    └── analyzer.py     # Gemini-based trend analysis and idea generation
```

## Development

```bash
pip install -e ".[dev]"

ruff check src/
pytest
```

## License

MIT
