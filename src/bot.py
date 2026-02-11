"""Telegram bot module for sending daily idea suggestions."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.analyzer import AnalysisResult, IdeaSuggestion


def format_idea_message(result: AnalysisResult, topic: str = "AI agent") -> str:
    """Format analysis result into a Telegram-friendly message."""
    lines = [
        f"🎯 *오늘의 {topic} 아이디어*",
        "",
        f"📊 *트렌드 요약*",
        result.trend_summary,
        "",
        "─" * 30,
    ]

    for i, idea in enumerate(result.ideas, 1):
        lines.extend(_format_single_idea(i, idea))

    lines.extend([
        "",
        "─" * 30,
        "💡 _하나 골라서 오늘 만들어보세요!_",
    ])

    return "\n".join(lines)


def _format_single_idea(index: int, idea: IdeaSuggestion) -> list[str]:
    """Format a single idea suggestion."""
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
        idea.difficulty.lower(), "⚪"
    )

    return [
        "",
        f"*{index}. {idea.title}* {difficulty_emoji}",
        "",
        f"📝 {idea.description}",
        "",
        f"⏰ *왜 지금?* {idea.why_now}",
        "",
        f"🛠 *스택:* {', '.join(idea.tech_stack)}",
        "",
        f"👉 *첫 단계:* {idea.first_step}",
    ]


class IdeaBot:
    """Telegram bot for daily idea suggestions."""

    def __init__(self, token: str, topic: str = "AI agent"):
        self.token = token
        self.topic = topic
        self.app = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register command handlers."""
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("help", self._handle_help))
        self.app.add_handler(CommandHandler("idea", self._handle_idea))
        self.app.add_handler(CommandHandler("status", self._handle_status))

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if update.effective_chat is None:
            return

        await update.effective_chat.send_message(
            f"👋 *Daily Idea Bot*에 오신 걸 환영합니다!\n\n"
            f"매일 아침 *{self.topic}* 아이디어를 보내드립니다.\n\n"
            f"*명령어:*\n"
            f"/idea - 지금 바로 아이디어 받기\n"
            f"/status - 봇 상태 확인\n"
            f"/help - 도움말",
            parse_mode="Markdown",
        )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if update.effective_chat is None:
            return

        await update.effective_chat.send_message(
            f"🤖 *Daily Idea Bot 사용법*\n\n"
            f"이 봇은 트렌드를 분석해서 *{self.topic}* 아이디어를 제안합니다.\n\n"
            f"*명령어:*\n"
            f"• /idea - 즉시 오늘의 아이디어 3개 받기\n"
            f"• /status - 봇 상태 및 다음 전송 시간\n"
            f"• /help - 이 도움말\n\n"
            f"매일 정해진 시간에 자동으로 아이디어가 전송됩니다.",
            parse_mode="Markdown",
        )

    async def _handle_idea(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /idea command - generate ideas on demand."""
        if update.effective_chat is None:
            return

        await update.effective_chat.send_message(
            "🔍 트렌드 수집 중... 잠시만 기다려주세요.",
            parse_mode="Markdown",
        )

        # The actual idea generation will be triggered from main.py
        # Store chat_id in context for callback
        context.user_data["pending_idea_request"] = True

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if update.effective_chat is None:
            return

        await update.effective_chat.send_message(
            "✅ *봇 상태: 정상*\n\n"
            "다음 자동 전송 시간은 설정된 스케줄을 확인하세요.",
            parse_mode="Markdown",
        )

    async def send_ideas(self, chat_id: int | str, result: AnalysisResult) -> None:
        """Send formatted ideas to a specific chat."""
        message = format_idea_message(result, self.topic)
        await self.app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
        )

    async def send_error(self, chat_id: int | str, error: str) -> None:
        """Send error message to a specific chat."""
        await self.app.bot.send_message(
            chat_id=chat_id,
            text=f"❌ *오류 발생*\n\n{error}",
            parse_mode="Markdown",
        )

    def run_polling(self) -> None:
        """Run the bot in polling mode (blocking)."""
        self.app.run_polling()
