import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AdminAccessTests(unittest.TestCase):
    @patch.dict(os.environ, {"ADMIN_IDS": "111,222"}, clear=False)
    @patch("bot.handlers.admin.get_setting_value", return_value="222,333")
    def test_admin_ids_merge_env_and_db(self, mock_get_setting):
        import bot.handlers.admin as admin_module

        self.assertTrue(admin_module.is_admin(111))
        self.assertTrue(admin_module.is_admin(333))
        self.assertFalse(admin_module.is_admin(999))
        mock_get_setting.assert_called()


class WebAdminRouteTests(unittest.TestCase):
    def setUp(self):
        from web.app import create_app

        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    @patch("web.routes.upsert_setting")
    @patch("web.routes.get_setting_value")
    def test_add_admin_route_saves_new_id(self, mock_get_setting, mock_upsert_setting):
        mock_get_setting.side_effect = lambda key, default=None: "111,222" if key == "admin_ids" else default

        response = self.client.post(
            "/settings/admin/add",
            data={"admin_telegram_id": "333"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        mock_upsert_setting.assert_called_once_with(
            "admin_ids",
            "111,222,333",
            description="Admin Telegram ID ro'yxati",
        )

    @patch.dict(os.environ, {"ADMIN_IDS": "111"}, clear=False)
    @patch("web.routes.upsert_setting")
    @patch("web.routes.get_setting_value")
    def test_remove_admin_route_updates_db_list(self, mock_get_setting, mock_upsert_setting):
        mock_get_setting.side_effect = lambda key, default=None: "111,222" if key == "admin_ids" else default

        response = self.client.post("/settings/admin/remove/222", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        mock_upsert_setting.assert_called_once_with(
            "admin_ids",
            "111",
            description="Admin Telegram ID ro'yxati",
        )

    @patch.dict(os.environ, {"ADMIN_IDS": "111"}, clear=False)
    @patch("web.routes.upsert_setting")
    @patch("web.routes.get_setting_value", return_value="")
    def test_remove_env_only_admin_does_not_touch_db(self, mock_get_setting, mock_upsert_setting):
        response = self.client.post("/settings/admin/remove/111", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        mock_upsert_setting.assert_not_called()

    @patch("web.routes.upsert_setting")
    @patch("web.routes.get_setting_value", return_value="")
    def test_add_admin_route_rejects_invalid_username(self, mock_get_setting, mock_upsert_setting):
        response = self.client.post(
            "/settings/admin/add",
            data={"admin_telegram_id": "@teacher"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        mock_upsert_setting.assert_not_called()


if __name__ == "__main__":
    unittest.main()
