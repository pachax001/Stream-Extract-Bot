"""Regression tests for config, stream state and cleanup. No Telegram credentials required."""
import json
import os
import shutil
import subprocess
import sys
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


class AutomaticUpdateTests(unittest.TestCase):
    @staticmethod
    def _run_git(cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def test_configured_branch_replaces_tracked_edits_and_preserves_config(self):
        """The configured remote is authoritative without removing config.env."""
        if not shutil.which("git"):
            self.skipTest("Git is not installed")
        from update import update_repository

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            deployed = Path(directory) / "deployed"
            source.mkdir()
            self._run_git(source, "init", "-b", "main")
            self._run_git(source, "config", "user.email", "tests@example.invalid")
            self._run_git(source, "config", "user.name", "CI Bot")
            (source / "version.txt").write_text("v1", encoding="utf-8")
            self._run_git(source, "add", "version.txt")
            self._run_git(source, "commit", "-m", "initial")
            self._run_git(source, "clone", str(source), str(deployed))

            (deployed / "config.env").write_text('BOT_TOKEN="unchanged"\n', encoding="utf-8")
            (deployed / "version.txt").write_text("local edited", encoding="utf-8")
            (source / "version.txt").write_text("v2", encoding="utf-8")
            self._run_git(source, "commit", "-am", "upstream update")

            with patch("update.PROJECT_ROOT", deployed):
                self.assertTrue(update_repository(str(source), "main"))
                self.assertEqual((deployed / "version.txt").read_text(encoding="utf-8"), "v2")
                self.assertEqual(
                    (deployed / "config.env").read_text(encoding="utf-8"),
                    'BOT_TOKEN="unchanged"\n',
                )

                # A bad configured branch cannot overwrite the installed code.
                (deployed / "version.txt").write_text("local still here", encoding="utf-8")
                self.assertFalse(update_repository(str(source), "missing-branch"))
                self.assertEqual(
                    (deployed / "version.txt").read_text(encoding="utf-8"),
                    "local still here",
                )

    def test_startup_updates_before_launch_even_after_git_failure(self):
        """start.sh invokes the updater first, and always starts the bot."""
        with tempfile.TemporaryDirectory() as directory:
            workdir = Path(directory)
            startup = (Path(__file__).resolve().parents[1] / "start.sh").resolve()
            for update_exit_code in (0, 1):
                output = workdir / "sequence.txt"
                output.unlink(missing_ok=True)
                (workdir / "update.py").write_text(
                    "from pathlib import Path\n"
                    "with Path('sequence.txt').open('a') as log: log.write('update\\n')\n"
                    f"raise SystemExit({update_exit_code})\n",
                    encoding="utf-8",
                )
                (workdir / "main.py").write_text(
                    "from pathlib import Path\n"
                    "with Path('sequence.txt').open('a') as log: log.write('main\\n')\n",
                    encoding="utf-8",
                )
                process = subprocess.run(
                    ["sh", str(startup)],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(
                    output.read_text(encoding="utf-8").splitlines(),
                    ["update", "main"],
                )


class RestartUpdateTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_runs_updater_before_replacing_process(self):
        from plugins.start import restart_command
        from plugins import start as start_module

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            message = SimpleNamespace(
                reply_text=AsyncMock(return_value=SimpleNamespace(id=12345)),
            )
            child = SimpleNamespace(
                returncode=0,
                communicate=AsyncMock(return_value=(b"updated", b"")),
            )
            with (
                patch.object(start_module, "RESTART_FILE", root / "restart_id.txt"),
                patch.object(start_module, "DOWNLOADS_DIR", root / "downloads"),
                patch.object(start_module.asyncio, "create_subprocess_exec", new=AsyncMock(return_value=child)) as spawn,
                patch.object(start_module.os, "execv", side_effect=RuntimeError("fake process replacement")) as replace,
            ):
                with self.assertRaisesRegex(RuntimeError, "fake process replacement"):
                    await restart_command(None, message)
                spawn.assert_awaited_once_with(
                    sys.executable, "update.py",
                    stdout=start_module.asyncio.subprocess.PIPE,
                    stderr=start_module.asyncio.subprocess.PIPE,
                )
                replace.assert_called_once_with(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    unittest.main()
