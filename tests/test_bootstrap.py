import os
import sys
import unittest
from unittest.mock import call, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BootstrapRuntimeTests(unittest.TestCase):
    @patch("services.bootstrap._configure_sentry")
    @patch("services.bootstrap.configure_observability")
    @patch("services.bootstrap._load_env_files")
    @patch("services.bootstrap.configure_async_runtime")
    @patch("services.bootstrap.logging.basicConfig")
    @patch("services.bootstrap.LOG_DIR")
    def test_bootstrap_runtime_loads_env_and_render_files(
        self,
        mock_log_dir,
        mock_basic_config,
        mock_async_runtime,
        mock_load_env_files,
        mock_observability,
        mock_sentry,
    ):
        import services.bootstrap as bootstrap

        bootstrap._runtime_bootstrapped = False
        try:
            bootstrap.bootstrap_runtime()
        finally:
            bootstrap._runtime_bootstrapped = False

        mock_log_dir.mkdir.assert_called_once_with(exist_ok=True)
        mock_basic_config.assert_called_once()
        mock_async_runtime.assert_called_once()
        mock_load_env_files.assert_called_once()
        mock_observability.assert_called_once()
        mock_sentry.assert_called_once()

    @patch("services.bootstrap.load_dotenv")
    def test_load_env_files_reads_dotenv_and_env_render(self, mock_load_dotenv):
        import services.bootstrap as bootstrap

        bootstrap._load_env_files()

        mock_load_dotenv.assert_has_calls(
            [
                call(dotenv_path=bootstrap.BASE_DIR / ".env", override=False),
                call(dotenv_path=bootstrap.BASE_DIR / ".env_render", override=False),
            ]
        )


if __name__ == "__main__":
    unittest.main()
