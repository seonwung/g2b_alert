import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from g2b_alert.api.attachment_downloader import (
    AttachmentDownloader,
    safe_path_component,
)


class AttachmentDownloaderTest(unittest.TestCase):
    def test_downloads_to_sanitized_business_folder_and_reuses_existing_file(self):
        response = Mock()
        response.headers = {
            "Content-Disposition": "attachment; filename*=UTF-8''%EA%B7%9C%EA%B2%A9%EC%84%9C.pdf"
        }
        response.iter_content.return_value = [b"document"]
        response.raise_for_status.return_value = None
        notice = SimpleNamespace(
            title='2026 탄소중립: 설비/투자',
            pre_spec_no="R26BD1",
            raw={"specDocFileUrl1": "https://example.com/downloadFile.do?id=1"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = AttachmentDownloader(temp_dir)
            with patch(
                "g2b_alert.api.attachment_downloader.requests.get",
                return_value=response,
            ):
                first = downloader.download_for_notice(notice)
                second = downloader.download_for_notice(notice)

            expected = Path(temp_dir) / "2026 탄소중립_ 설비_투자" / "규격서.pdf"
            self.assertEqual(b"document", expected.read_bytes())
            self.assertEqual([expected], first["downloaded"])
            self.assertEqual([expected], second["existing"])

    def test_rejects_reserved_windows_path_names(self):
        self.assertEqual("_CON", safe_path_component("CON", "fallback"))

    def test_overwrite_replaces_same_named_changed_file(self):
        response = Mock()
        response.headers = {"Content-Disposition": "attachment; filename=spec.pdf"}
        response.raise_for_status.return_value = None
        notice = SimpleNamespace(
            title="변경공고",
            bid_no="R1",
            raw={"ntceSpecDocUrl1": "https://example.com/spec"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "변경공고" / "spec.pdf"
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"old")
            response.iter_content.return_value = [b"new"]
            with patch(
                "g2b_alert.api.attachment_downloader.requests.get",
                return_value=response,
            ):
                report = AttachmentDownloader(temp_dir).download_for_notice(
                    notice, overwrite=True
                )

            self.assertEqual(b"new", destination.read_bytes())
            self.assertEqual([destination], report["downloaded"])

    def test_overwrite_removes_obsolete_renamed_attachment(self):
        response = Mock()
        response.headers = {"Content-Disposition": "attachment; filename=new.pdf"}
        response.raise_for_status.return_value = None
        response.iter_content.return_value = [b"new"]
        notice = SimpleNamespace(
            title="변경공고",
            bid_no="R1",
            raw={"ntceSpecDocUrl1": "https://example.com/new"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir) / "변경공고"
            folder.mkdir(parents=True)
            old_file = folder / "old.pdf"
            old_file.write_bytes(b"old")
            with patch(
                "g2b_alert.api.attachment_downloader.requests.get",
                return_value=response,
            ):
                report = AttachmentDownloader(temp_dir).download_for_notice(
                    notice, overwrite=True
                )

            self.assertFalse(old_file.exists())
            self.assertEqual(b"new", (folder / "new.pdf").read_bytes())
            self.assertEqual([old_file.resolve()], report["removed"])


if __name__ == "__main__":
    unittest.main()
