"""Tests for application configuration persistence."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g2b_alert.model.config import AppConfig, load_config, save_config
from g2b_alert.model.credentials import CredentialStoreError


class ConfigManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_api_key_is_stored_in_keyring_and_omitted_from_json(self):
        with patch("g2b_alert.model.config.save_api_key") as save_key:
            save_config(AppConfig(api_key="secret-key", interval="5"), self.path)

        saved = json.loads(self.path.read_text(encoding="utf-8"))
        save_key.assert_called_once_with("secret-key")
        self.assertEqual("", saved["api_key"])
        self.assertFalse(self.path.with_name(".config.json.tmp").exists())

    def test_loads_api_key_from_keyring_when_json_has_none(self):
        self.path.write_text(json.dumps({"api_key": "", "interval": "7"}), encoding="utf-8")
        with patch("g2b_alert.model.config.get_api_key", return_value="stored-key"):
            config = load_config(self.path)
        self.assertEqual("stored-key", config.api_key)
        self.assertEqual("7", config.interval)

    def test_keeps_plaintext_fallback_if_keyring_is_unavailable(self):
        with patch(
            "g2b_alert.model.config.save_api_key",
            side_effect=CredentialStoreError("unavailable"),
        ):
            save_config(AppConfig(api_key="fallback-key"), self.path)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual("fallback-key", saved["api_key"])

    def test_keyword_row_rules_round_trip(self):
        rules = [
            {
                "id": "rule-1",
                "keyword": "BIS",
                "operator": "or",
                "categories": ["service", "goods"],
                "targets": ["bid_lifecycle"],
                "enabled": True,
            }
        ]
        with patch("g2b_alert.model.config.save_api_key"):
            save_config(AppConfig(keyword_rules=rules), self.path)
        with patch("g2b_alert.model.config.get_api_key", return_value=""):
            loaded = load_config(self.path)
        self.assertEqual(rules, loaded.keyword_rules)

    def test_attachment_download_directory_round_trip(self):
        download_dir = str(Path(self.temp_dir.name) / "company-files")
        with patch("g2b_alert.model.config.save_api_key"):
            save_config(AppConfig(attachment_download_dir=download_dir), self.path)
        with patch("g2b_alert.model.config.get_api_key", return_value=""):
            loaded = load_config(self.path)

        self.assertEqual(download_dir, loaded.attachment_download_dir)

    def test_legacy_keyword_fields_are_migrated_before_the_view_receives_them(self):
        self.path.write_text(
            json.dumps(
                {
                    "keywords": "",
                    "and_keywords": "server",
                    "or_keywords": "network, storage",
                    "exclude_keywords": "used",
                    "selected_categories": ["goods"],
                    "prespec_search_enabled": True,
                }
            ),
            encoding="utf-8",
        )

        with patch("g2b_alert.model.config.get_api_key", return_value=""):
            first = load_config(self.path)
            second = load_config(self.path)

        self.assertEqual(
            ["server", "network", "storage", "used"],
            [rule["keyword"] for rule in first.keyword_rules],
        )
        self.assertEqual(
            ["and", "or", "or", "exclude"],
            [rule["operator"] for rule in first.keyword_rules],
        )
        self.assertTrue(
            all(rule["categories"] == ["goods"] for rule in first.keyword_rules)
        )
        self.assertTrue(
            all(
                rule["targets"] == ["bid_lifecycle", "prespec"]
                for rule in first.keyword_rules
            )
        )
        self.assertEqual(
            [rule["id"] for rule in first.keyword_rules],
            [rule["id"] for rule in second.keyword_rules],
        )


if __name__ == "__main__":
    unittest.main()
