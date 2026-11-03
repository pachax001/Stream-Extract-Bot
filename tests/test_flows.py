"""Regression tests for config, stream state and cleanup. No Telegram credentials required."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "123:dummy")
os.environ.setdefault("APP_ID", "12345")
os.environ.setdefault("API_HASH", "not-a-real-api-hash")
os.environ.setdefault("BOT_USERNAME", "examplebot")
os.environ.setdefault("OWNER_ID", "123")

from config import _get_env
from helpers.download import _probe_and_ask_streams
from helpers.progress import stream_selections, download_progress
from helpers.tools import execute
from helpers.upload import _common_upload_logic


class ConfigurationTests(unittest.TestCase):
    def test_blank_optional_numeric_setting_uses_default(self):
        with patch.dict(os.environ, {"THRESHOLD": "", "MAX_DOWNLOAD_LIMIT": ""}):
            self.assertEqual(_get_env("THRESHOLD", cast=int, default="50"), 50)
            self.assertEqual(_get_env("MAX_DOWNLOAD_LIMIT", cast=int, default="10"), 10)

    def test_all_plugins_import_under_wzgram(self):
        import importlib
        for name in ("plugins.start", "plugins.extractor", "plugins.callback"):
            with self.subTest(module=name):
                self.assertIsNotNone(importlib.import_module(name))

    def test_app_manifest_is_valid_json(self):
        data = json.loads(Path("app.json").read_text(encoding="utf-8"))
        self.assertIn("BOT_TOKEN", data["env"])


class TransferTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        stream_selections.clear()
        download_progress.clear()

    async def asyncTearDown(self):
        stream_selections.clear()
        download_progress.clear()

    async def test_video_stream_metadata_matches_extractor(self):
        status = SimpleNamespace(
            chat=SimpleNamespace(id=123), id=456, edit_text=AsyncMock()
        )
        original = SimpleNamespace(
            from_user=SimpleNamespace(id=789, first_name="Tester")
        )
        streams = {"streams": [
            {"index": 1, "codec_type": "audio", "codec_name": "aac", "tags": {"language": "eng"}},
            {"index": 2, "codec_type": "subtitle", "codec_name": "subrip"},
        ]}
        with patch("helpers.download.execute", new=AsyncMock(
            return_value=(json.dumps(streams), "", 0, 99)
        )):
            ok = await _probe_and_ask_streams(
                Path("/tmp/test-video.mkv"), "test-video.mkv", status, original
            )
        self.assertTrue(ok)
        entry = stream_selections["123-456"]["1"]
        self.assertEqual(entry["file_path"], "/tmp/test-video.mkv")
        self.assertEqual(entry["codec_name"], "aac")
        self.assertEqual(entry["stream_type"], "audio")
        self.assertEqual(entry["user_id"], 789)
        self.assertFalse(download_progress)

    async def test_upload_without_telegram_confirmation_fails_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "subtitle.srt"
            output.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello")
            status = SimpleNamespace(
                chat=SimpleNamespace(id=123), id=456, delete=AsyncMock()
            )
            original = SimpleNamespace(
                chat=SimpleNamespace(id=123), id=456,
                edit_text=AsyncMock(return_value=status)
            )
            client = SimpleNamespace(send_document=AsyncMock(return_value=None))
            result = await _common_upload_logic(
                client, original, str(output), "subtitle.srt", 789, "Tester", "subtitle"
            )
            self.assertFalse(result)
            self.assertFalse(output.exists())

    async def test_failed_process_spawn_is_reported(self):
        out, err, code, pid = await execute(["/nonexistent-wzgram-test-program"])
        self.assertEqual(code, -1)
        self.assertEqual(pid, 0)


if __name__ == "__main__":
    unittest.main()
