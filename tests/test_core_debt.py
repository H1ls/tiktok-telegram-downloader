from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.config import AppConfig
from core.command_aliases import CommandValidationError, normalize_command_aliases
from core.paths import get_user_dir
from core.rate_limiter import AsyncRateLimiter
from core.updater import _parse_sha256, _sha256_file, _write_windows_updater, find_git_repo


class ConfigValidationTests(unittest.TestCase):
    def test_validate_clamps_batch_size_and_defaults(self) -> None:
        cfg = AppConfig(
            batch_size=-5,
            defaults={"batch_size": 100, "queue_keep_max": 0, "delivery_mode": ""},
        )

        cfg.validate()

        self.assertEqual(cfg.batch_size, 1)
        self.assertEqual(cfg.defaults["batch_size"], 10)
        self.assertEqual(cfg.defaults["queue_keep_max"], 50)
        self.assertEqual(cfg.defaults["delivery_mode"], "dm")

    def test_command_aliases_are_normalized(self) -> None:
        aliases = normalize_command_aliases({"start": "start, начало, запуск"})

        self.assertEqual(aliases["start"], ["start", "начало", "запуск"])

    def test_command_aliases_reject_duplicates_between_handlers(self) -> None:
        with self.assertRaises(CommandValidationError):
            normalize_command_aliases({"start": "start, go", "my": "my, go"})


class PathValidationTests(unittest.TestCase):
    def test_get_user_dir_rejects_non_integer_user_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cfg = AppConfig(download_root=temp_dir)

            with self.assertRaises(TypeError):
                get_user_dir(cfg, "../bad")  # type: ignore[arg-type]


class UpdaterTests(unittest.TestCase):
    def test_find_git_repo_walks_up_from_child_directory(self) -> None:
        repo = find_git_repo(Path("dist"))

        self.assertIsNotNone(repo)
        self.assertTrue((repo / ".git").exists())

    def test_parse_sha256_supports_named_file_format(self) -> None:
        expected = "a" * 64
        content = f"{expected}  tiktok-telegram-downloader.exe\n"

        self.assertEqual(_parse_sha256(content, "tiktok-telegram-downloader.exe"), expected)

    def test_parse_sha256_supports_single_hash_format(self) -> None:
        expected = "b" * 64

        self.assertEqual(_parse_sha256(expected, "tiktok-telegram-downloader.exe"), expected)

    def test_parse_sha256_rejects_missing_file_hash(self) -> None:
        content = f"{'c' * 64}  other.exe\n"

        with self.assertRaises(ValueError):
            _parse_sha256(content, "tiktok-telegram-downloader.exe")

    def test_sha256_file_hashes_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.bin"
            path.write_bytes(b"abc")

            self.assertEqual(
                _sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_windows_updater_uses_powershell_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = _write_windows_updater(root / "app.exe", root / "app.download")
            content = script.read_text(encoding="utf-8-sig")

            self.assertEqual(script.suffix, ".ps1")
            self.assertIn("Move-Item -LiteralPath", content)
            self.assertIn("Start-Process -FilePath", content)


class RateLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def test_acquire_allows_calls_within_limit(self) -> None:
        limiter = AsyncRateLimiter(max_calls=2, window_seconds=1.0)

        await limiter.acquire()
        await limiter.acquire()

    async def test_acquire_waits_after_limit(self) -> None:
        limiter = AsyncRateLimiter(max_calls=1, window_seconds=0.01)

        await limiter.acquire()
        await limiter.acquire()

    def test_rejects_invalid_limits(self) -> None:
        with self.assertRaises(ValueError):
            AsyncRateLimiter(max_calls=0, window_seconds=1.0)
        with self.assertRaises(ValueError):
            AsyncRateLimiter(max_calls=1, window_seconds=0)


if __name__ == "__main__":
    unittest.main()
