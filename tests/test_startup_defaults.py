import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StartupDefaultsTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "BOT_TOKEN": "bot-token",
            "ADMIN_IDS": "1,2,3",
            "TEACHER_USERNAME": "@teacher",
            "CHANNEL_ID": "@my_channel",
        },
        clear=False,
    )
    @patch("services.startup_defaults.upsert_setting")
    @patch("services.startup_defaults.get_setting_value", return_value="")
    def test_sync_startup_defaults_seeds_settings(self, mock_get_setting_value, mock_upsert_setting):
        from services.startup_defaults import sync_startup_defaults

        with patch("services.startup_defaults.get_session") as mock_get_session:
            session = MagicMock()
            session.query.return_value.all.return_value = []
            mock_get_session.return_value = session
            sync_startup_defaults()

        calls = [call.args[:2] for call in mock_upsert_setting.call_args_list]
        self.assertIn(("bot_token", "bot-token"), calls)
        self.assertIn(("admin_ids", "1,2,3"), calls)
        self.assertIn(("teacher_username", "@teacher"), calls)
        self.assertIn(("channel_id", "@my_channel"), calls)
        mock_get_setting_value.assert_called()

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEYS": "or-1,or-2",
            "GROQ_API_KEY": "groq-1",
        },
        clear=False,
    )
    @patch("services.startup_defaults.upsert_setting")
    @patch("services.startup_defaults.get_setting_value", return_value="")
    def test_sync_startup_defaults_adds_missing_api_keys(
        self,
        mock_get_setting_value,
        mock_upsert_setting,
    ):
        from services.startup_defaults import sync_startup_defaults

        session = MagicMock()
        session.query.return_value.all.return_value = []

        with patch("services.startup_defaults.get_session", return_value=session):
            sync_startup_defaults()

        added_rows = [call.args[0] for call in session.add.call_args_list]
        services = [(row.service, row.api_key) for row in added_rows]
        self.assertIn(("openrouter", "or-1"), services)
        self.assertIn(("openrouter", "or-2"), services)
        self.assertIn(("groq", "groq-1"), services)
        session.commit.assert_called_once()
        mock_upsert_setting.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "or-1",
        },
        clear=False,
    )
    def test_sync_startup_defaults_reactivates_existing_key(self):
        from services.startup_defaults import sync_startup_defaults

        existing_row = SimpleNamespace(service="openrouter", api_key="or-1", is_active=False)
        session = MagicMock()
        session.query.return_value.all.return_value = [existing_row]

        with patch("services.startup_defaults.get_session", return_value=session):
            with patch("services.startup_defaults.upsert_setting"), patch(
                "services.startup_defaults.get_setting_value",
                return_value="",
            ):
                sync_startup_defaults()

        self.assertTrue(existing_row.is_active)
        session.commit.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("services.startup_defaults.upsert_setting")
    @patch("services.startup_defaults.get_setting_value", return_value="")
    def test_sync_startup_defaults_skips_empty_env(self, mock_get_setting_value, mock_upsert_setting):
        from services.startup_defaults import sync_startup_defaults

        session = MagicMock()
        session.query.return_value.all.return_value = []

        with patch("services.startup_defaults.get_session", return_value=session):
            sync_startup_defaults()

        mock_upsert_setting.assert_not_called()
        session.add.assert_not_called()
        session.commit.assert_not_called()
        mock_get_setting_value.assert_not_called()

    @patch.dict(os.environ, {"ADMIN_IDS": "1,2"}, clear=False)
    @patch("services.startup_defaults.upsert_setting")
    @patch("services.startup_defaults.get_setting_value", return_value="2,3")
    def test_sync_startup_defaults_merges_admin_ids(
        self,
        mock_get_setting_value,
        mock_upsert_setting,
    ):
        from services.startup_defaults import sync_startup_defaults

        session = MagicMock()
        session.query.return_value.all.return_value = []

        with patch("services.startup_defaults.get_session", return_value=session):
            sync_startup_defaults()

        mock_upsert_setting.assert_any_call(
            "admin_ids",
            "1,2,3",
            description="Admin Telegram ID ro'yxati",
        )
        mock_get_setting_value.assert_called()


if __name__ == "__main__":
    unittest.main()
