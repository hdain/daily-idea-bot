"""LLM-based trend analyzer and idea generator using Google Gemini."""

import json

from google import genai
from pydantic import BaseModel

from src.scraper import TrendItem


class IdeaSuggestion(BaseModel):
    """A single idea suggestion."""

    title: str
    description: str
    why_now: str  # Why this is relevant based on trends
    difficulty: str  # easy, medium, hard
    tech_stack: list[str]
    first_step: str


class AnalysisResult(BaseModel):
    """Complete analysis result with multiple ideas."""

    trend_summary: str
    ideas: list[IdeaSuggestion]


SYSTEM_PROMPT_TEMPLATE = """You are a creative idea generator for developers.
Your job is to analyze current tech trends and suggest creative, practical project ideas
related to the topic: "{topic}".

Guidelines:
- All ideas MUST be related to "{topic}"
- Ideas should be buildable in 1 day (MVP)
- Be specific and actionable
- Consider what's trending NOW and why it matters
- Avoid generic or overdone ideas - be creative!
- Each idea should leverage current trends in a unique way

Output in Korean (한국어로 답변해주세요).

You MUST respond with valid JSON in this exact format:
{{
  "trend_summary": "트렌드 요약 (2-3문장)",
  "ideas": [
    {{
      "title": "아이디어 제목",
      "description": "아이디어 설명",
      "why_now": "왜 지금인지",
      "difficulty": "easy|medium|hard",
      "tech_stack": ["기술1", "기술2"],
      "first_step": "첫 번째 단계"
    }}
  ]
}}"""

USER_PROMPT_TEMPLATE = """Based on today's tech trends, suggest 3 project ideas
related to "{topic}".

## Today's Trends

{trends}

---

Analyze these trends and suggest 3 creative "{topic}" ideas that:
1. Are inspired by or leverage these trends
2. Can be built as an MVP in one day
3. Solve a real problem
4. Are NOT just clones of existing tools

Respond with valid JSON only. No markdown, no explanation outside the JSON."""


class TrendAnalyzer:
    """Analyzes trends and generates project ideas using Gemini."""

    def __init__(self, gemini_api_key: str, topic: str = "AI agent"):
        self.client = genai.Client(api_key=gemini_api_key)
        self.topic = topic

    async def analyze_and_generate(self, trends: list[TrendItem]) -> AnalysisResult:
        """Analyze trends and generate project ideas."""
        trends_text = self._format_trends(trends)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(topic=self.topic)
        user_prompt = USER_PROMPT_TEMPLATE.format(topic=self.topic, trends=trends_text)
        prompt = f"{system_prompt}\n\n{user_prompt}"

        response = await self.client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "temperature": 0.8,
                "response_mime_type": "application/json",
            },
        )

        # Parse JSON response
        try:
            data = json.loads(response.text)
            return AnalysisResult(**data)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Failed to parse Gemini response: {e}\nResponse: {response.text}")

    def _format_trends(self, trends: list[TrendItem]) -> str:
        """Format trend items into readable text."""
        grouped: dict[str, list[TrendItem]] = {}
        for trend in trends:
            if trend.source not in grouped:
                grouped[trend.source] = []
            grouped[trend.source].append(trend)

        lines = []
        for source, items in grouped.items():
            lines.append(f"### {source}")
            for item in items[:10]:  # Limit per source
                score_str = f" (score: {item.score})" if item.score else ""
                desc_str = f"\n   {item.description[:100]}..." if item.description else ""
                lines.append(f"- {item.title}{score_str}{desc_str}")
            lines.append("")

        return "\n".join(lines)
