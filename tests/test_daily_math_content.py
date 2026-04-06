import unittest
from datetime import datetime
from types import SimpleNamespace

from services import daily_math_content
from services.daily_math_content import DailyContentMessage


class _FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, disable_web_page_preview=False):
        self.messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": disable_web_page_preview,
            }
        )


class DailyMathContentTests(unittest.IsolatedAsyncioTestCase):
    def test_should_send_now_respects_local_schedule(self):
        original_get_setting_int = daily_math_content.get_setting_int
        daily_math_content.get_setting_int = lambda key, default, min_value=None, max_value=None: 9 if key == "daily_content_hour" else 0
        try:
            before = datetime(2026, 4, 5, 8, 45)
            after = datetime(2026, 4, 5, 9, 5)
            self.assertFalse(daily_math_content.should_send_now(before))
            self.assertTrue(daily_math_content.should_send_now(after))
        finally:
            daily_math_content.get_setting_int = original_get_setting_int

    async def test_check_and_send_daily_content_sends_only_once_per_day(self):
        sent_dates = set()
        original_has_sent = daily_math_content._sync_has_sent_today
        original_save_sent = daily_math_content._sync_save_sent_content
        original_get_content = daily_math_content.get_daily_math_content

        daily_math_content._sync_has_sent_today = lambda date_str: date_str in sent_dates

        def _save_sent(content_text, content_type, scheduled_time):
            sent_dates.add(scheduled_time)
            return 1

        async def _fake_content(now=None):
            return DailyContentMessage(
                text="📘 <b>Sinov posti</b>\n\nBu kundalik matematika posti.",
                content_type="fact",
                title="Sinov",
            )

        daily_math_content._sync_save_sent_content = _save_sent
        daily_math_content.get_daily_math_content = _fake_content
        bot = _FakeBot()
        now = datetime(2026, 4, 5, 10, 0)

        try:
            first = await daily_math_content.check_and_send_daily_content(bot, "@test_channel", now=now)
            second = await daily_math_content.check_and_send_daily_content(bot, "@test_channel", now=now)
        finally:
            daily_math_content._sync_has_sent_today = original_has_sent
            daily_math_content._sync_save_sent_content = original_save_sent
            daily_math_content.get_daily_math_content = original_get_content

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(bot.messages), 1)

    async def test_get_daily_math_content_falls_back_when_sources_absent(self):
        original_birthday = daily_math_content._build_birthday_content
        original_topic = daily_math_content._build_topic_content

        async def _none(*args, **kwargs):
            return None

        daily_math_content._build_birthday_content = _none
        daily_math_content._build_topic_content = _none
        try:
            payload = await daily_math_content.get_daily_math_content(datetime(2026, 4, 5, 10, 0))
        finally:
            daily_math_content._build_birthday_content = original_birthday
            daily_math_content._build_topic_content = original_topic

        self.assertTrue(payload.text)
        self.assertGreater(len(payload.text), 150)

    async def test_manual_force_send_bypasses_daily_limit(self):
        original_has_sent = daily_math_content._sync_has_sent_today
        original_save_sent = daily_math_content._sync_save_sent_content
        original_get_content = daily_math_content.get_daily_math_content

        daily_math_content._sync_has_sent_today = lambda date_str: True
        daily_math_content._sync_save_sent_content = lambda content_text, content_type, scheduled_time: 1

        async def _fake_content(now=None):
            return DailyContentMessage(
                text="📘 <b>Majburiy post</b>",
                content_type="fact",
                title="Majburiy",
            )

        daily_math_content.get_daily_math_content = _fake_content
        bot = _FakeBot()
        now = datetime(2026, 4, 5, 10, 0)

        try:
            result = await daily_math_content.check_and_send_daily_content(
                bot,
                "@test_channel",
                force=True,
                now=now,
            )
        finally:
            daily_math_content._sync_has_sent_today = original_has_sent
            daily_math_content._sync_save_sent_content = original_save_sent
            daily_math_content.get_daily_math_content = original_get_content

        self.assertTrue(result)
        self.assertEqual(len(bot.messages), 1)

    async def test_birthday_content_skips_untranslated_english_sections(self):
        original_fetch_today_births = daily_math_content._fetch_today_births
        original_fetch_summary = daily_math_content._fetch_wikipedia_summary
        original_retrieve = daily_math_content.knowledge_retriever.retrieve
        original_localize_sections = daily_math_content._localize_content_sections
        original_localize_block = daily_math_content._localize_single_block

        async def _fake_births(now=None):
            return [
                {
                    "text": "Maimonides, Jewish philosopher and mathematician",
                    "pages": [
                        {
                            "title": "Maimonides",
                            "content_urls": {
                                "desktop": {
                                    "page": "https://en.wikipedia.org/wiki/Maimonides",
                                }
                            },
                        }
                    ],
                }
            ]

        async def _fake_summary(title):
            return {
                "extract": (
                    "Moses ben Maimon, commonly known as Maimonides, was a Jewish philosopher, "
                    "rabbi and physician whose long biography remains fully in English here."
                ),
                "content_urls": {
                    "desktop": {
                        "page": "https://en.wikipedia.org/wiki/Maimonides",
                    }
                },
            }

        def _fake_retrieve(*args, **kwargs):
            return SimpleNamespace(
                structured=SimpleNamespace(
                    important_facts=["He became one of the most influential thinkers of the Middle Ages."],
                    rules=[],
                    definitions=[],
                    examples=["He wrote works that later influenced mathematics education."],
                ),
                sources=[SimpleNamespace(url="https://example.com")],
            )

        async def _fake_localize_sections(title, intro, extract, importance, force=False):
            return intro, extract, importance

        async def _fake_localize_block(title, text, force=False):
            return text

        daily_math_content._fetch_today_births = _fake_births
        daily_math_content._fetch_wikipedia_summary = _fake_summary
        daily_math_content.knowledge_retriever.retrieve = _fake_retrieve
        daily_math_content._localize_content_sections = _fake_localize_sections
        daily_math_content._localize_single_block = _fake_localize_block

        try:
            payload = await daily_math_content._build_birthday_content(datetime(2026, 4, 6, 10, 0))
        finally:
            daily_math_content._fetch_today_births = original_fetch_today_births
            daily_math_content._fetch_wikipedia_summary = original_fetch_summary
            daily_math_content.knowledge_retriever.retrieve = original_retrieve
            daily_math_content._localize_content_sections = original_localize_sections
            daily_math_content._localize_single_block = original_localize_block

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
