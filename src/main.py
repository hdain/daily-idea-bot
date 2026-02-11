"""Main entry point for the Daily Idea Bot."""

import asyncio
import logging
import os
import sys
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes

from src.analyzer import TrendAnalyzer
from src.bot import IdeaBot
from src.scraper import TrendScraper

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class DailyIdeaService:
    """Main service that orchestrates scraping, analysis, and bot messaging."""

    def __init__(
        self,
        telegram_token: str,
        telegram_chat_id: str,
        gemini_api_key: str,
        sela_api_key: str | None = None,
        schedule_time: str = "09:00",
        enabled_scrapers: list[str] | None = None,
        idea_topic: str = "AI agent",
    ):
        self.chat_id = telegram_chat_id
        self.schedule_time = schedule_time
        self.idea_topic = idea_topic

        self.scraper = TrendScraper(
            sela_api_key=sela_api_key,
            enabled_scrapers=enabled_scrapers,
        )
        self.analyzer = TrendAnalyzer(gemini_api_key=gemini_api_key, topic=idea_topic)
        self.bot = IdeaBot(token=telegram_token, topic=idea_topic)
        self.scheduler = AsyncIOScheduler()

        # Add custom handler for /idea command
        self._setup_idea_handler()

    def _setup_idea_handler(self) -> None:
        """Override /idea handler to actually generate ideas."""
        from telegram.ext import CommandHandler

        # Remove existing handler
        for handler in self.bot.app.handlers.get(0, []):
            if isinstance(handler, CommandHandler) and "idea" in handler.commands:
                self.bot.app.remove_handler(handler)
                break

        # Add new handler with idea generation
        async def handle_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if update.effective_chat is None:
                return

            await update.effective_chat.send_message(
                "🔍 트렌드 수집 중... 잠시만 기다려주세요.",
            )

            try:
                await self._generate_and_send_ideas(update.effective_chat.id)
            except Exception as e:
                logger.error(f"Error generating ideas: {e}")
                await self.bot.send_error(update.effective_chat.id, str(e))

        self.bot.app.add_handler(CommandHandler("idea", handle_idea))

    async def _generate_and_send_ideas(self, chat_id: int | str) -> None:
        """Generate ideas from trends and send to chat."""
        logger.info("Starting trend collection...")

        # Collect trends
        trends = await self.scraper.get_all_trends()
        logger.info(f"Collected {len(trends)} trend items")

        if not trends:
            await self.bot.send_error(chat_id, "트렌드를 수집하지 못했습니다.")
            return

        # Analyze and generate ideas
        logger.info("Analyzing trends and generating ideas...")
        result = await self.analyzer.analyze_and_generate(trends)

        # Send to chat
        await self.bot.send_ideas(chat_id, result)
        logger.info("Ideas sent successfully")

    async def _scheduled_job(self) -> None:
        """Job that runs on schedule."""
        logger.info(f"Running scheduled job at {datetime.now()}")
        try:
            await self._generate_and_send_ideas(self.chat_id)
        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")
            await self.bot.send_error(self.chat_id, f"스케줄 작업 실패: {e}")

    def _setup_scheduler(self) -> None:
        """Setup the daily scheduler."""
        hour, minute = map(int, self.schedule_time.split(":"))

        self.scheduler.add_job(
            self._scheduled_job,
            CronTrigger(hour=hour, minute=minute),
            id="daily_ideas",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily job at {self.schedule_time}")

    async def start(self) -> None:
        """Start the bot and scheduler."""
        logger.info("Starting Daily Idea Bot...")

        # Setup and start scheduler
        self._setup_scheduler()
        self.scheduler.start()

        # Initialize bot
        await self.bot.app.initialize()
        await self.bot.app.start()
        await self.bot.app.updater.start_polling(drop_pending_updates=True)  # type: ignore

        logger.info("Bot is running. Press Ctrl+C to stop.")

        # Send startup message
        try:
            await self.bot.app.bot.send_message(
                chat_id=self.chat_id,
                text=f"🚀 *Daily Idea Bot 시작됨*\n\n"
                f"주제: *{self.idea_topic}*\n"
                f"매일 {self.schedule_time}에 아이디어를 보내드립니다.\n"
                f"/idea 명령어로 지금 바로 받을 수도 있어요!",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not send startup message: {e}")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop the bot and scheduler."""
        logger.info("Stopping Daily Idea Bot...")

        self.scheduler.shutdown()
        await self.scraper.close()

        await self.bot.app.updater.stop()  # type: ignore
        await self.bot.app.stop()
        await self.bot.app.shutdown()

        logger.info("Bot stopped.")


def main() -> None:
    """Main entry point."""
    load_dotenv()

    # Load configuration from environment
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    sela_api_key = os.getenv("SELA_API_KEY")
    schedule_time = os.getenv("DAILY_SCHEDULE_TIME", "09:00")
    idea_topic = os.getenv("IDEA_TOPIC", "AI agent")

    # Parse enabled scrapers from comma-separated string
    enabled_scrapers_str = os.getenv("ENABLED_SCRAPERS", "")
    enabled_scrapers = (
        [s.strip() for s in enabled_scrapers_str.split(",") if s.strip()]
        if enabled_scrapers_str
        else None  # Use default if not specified
    )

    # Validate required config
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN is required")
        sys.exit(1)
    if not telegram_chat_id:
        logger.error("TELEGRAM_CHAT_ID is required")
        sys.exit(1)
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY is required")
        sys.exit(1)

    # Create and run service
    service = DailyIdeaService(
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id,
        gemini_api_key=gemini_api_key,
        sela_api_key=sela_api_key,
        schedule_time=schedule_time,
        enabled_scrapers=enabled_scrapers,
        idea_topic=idea_topic,
    )

    # Run with proper signal handling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(service.start())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        loop.run_until_complete(service.stop())
        loop.close()


if __name__ == "__main__":
    main()
