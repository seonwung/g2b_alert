"""Download notice attachments into stable, business-name folders."""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from ..model.notice_detail_model import extract_attachments
from ..model.storage_paths import get_persistent_data_dir
from .pre_spec_api import filename_from_content_disposition


INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class AttachmentDownloader:
    def __init__(self, root_dir=None, timeout_seconds=30):
        self.set_root_dir(root_dir)
        self.timeout_seconds = timeout_seconds

    def set_root_dir(self, root_dir=None):
        self.root_dir = Path(root_dir or (get_persistent_data_dir() / "attachments"))

    def download_for_notice(self, notice, overwrite=False):
        attachments = extract_attachments(getattr(notice, "raw", None))
        attachments = _unique_url_attachments(attachments)
        if not attachments:
            return {
                "folder": None,
                "downloaded": [],
                "existing": [],
                "removed": [],
                "failed": [],
            }

        reference = (
            getattr(notice, "pre_spec_no", "")
            or getattr(notice, "bid_no", "")
            or "공고"
        )
        folder_name = safe_path_component(getattr(notice, "title", ""), reference)
        folder = self.root_dir / folder_name
        report = {
            "folder": folder,
            "downloaded": [],
            "existing": [],
            "removed": [],
            "failed": [],
        }

        for index, attachment in enumerate(attachments, start=1):
            self._download_one(folder, attachment, index, report, overwrite=overwrite)
        self._sync_managed_files(folder, report, overwrite=overwrite)
        return report

    def _download_one(self, folder, attachment, index, report, overwrite=False):
        url = str(attachment.get("url") or "").strip()
        if urlparse(url).scheme.lower() not in {"http", "https"}:
            report["failed"].append({"url": url, "error": "지원하지 않는 URL"})
            return

        response = None
        temp_path = None
        try:
            response = requests.get(url, stream=True, timeout=self.timeout_seconds)
            response.raise_for_status()
            header_name = filename_from_content_disposition(
                response.headers.get("Content-Disposition", "")
            )
            fallback_name = attachment.get("name") or _filename_from_url(url)
            if str(fallback_name).casefold().startswith("첨부파일"):
                fallback_name = ""
            filename = safe_path_component(
                header_name or fallback_name,
                f"첨부파일_{index}",
            )
            destination = folder / filename
            if destination.exists() and not overwrite:
                report["existing"].append(destination)
                return

            folder.mkdir(parents=True, exist_ok=True)
            temp_path = destination.with_name(f".{destination.name}.part")
            with temp_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        file.write(chunk)
            temp_path.replace(destination)
            report["downloaded"].append(destination)
        except requests.exceptions.RequestException as error:
            report["failed"].append({"url": url, "error": str(error)})
        except OSError as error:
            report["failed"].append({"url": url, "error": str(error)})
        finally:
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            if response is not None:
                response.close()

    def _sync_managed_files(self, folder, report, overwrite=False):
        if report["failed"] or not folder.exists():
            return
        current_paths = {
            Path(path).resolve()
            for path in (*report["downloaded"], *report["existing"])
        }
        if not current_paths:
            return

        manifest = folder / ".g2b-files.json"
        previous_paths = set()
        if manifest.exists():
            try:
                names = json.loads(manifest.read_text(encoding="utf-8"))
                previous_paths = {
                    (folder / str(name)).resolve()
                    for name in names
                    if Path(str(name)).name == str(name)
                }
            except (OSError, ValueError, TypeError):
                previous_paths = set()
        elif overwrite:
            # Adopt files from folders created by older app versions so the first
            # changed-notice refresh can remove obsolete attachments as requested.
            previous_paths = {
                path.resolve()
                for path in folder.iterdir()
                if path.is_file()
                and not path.name.startswith(".")
                and not path.name.endswith(".part")
            }

        if overwrite:
            for obsolete in previous_paths - current_paths:
                try:
                    obsolete.unlink()
                    report["removed"].append(obsolete)
                except FileNotFoundError:
                    pass
                except OSError as error:
                    report["failed"].append(
                        {"url": "", "error": f"이전 첨부파일 삭제 실패: {error}"}
                    )

        if report["failed"]:
            return
        temp_manifest = manifest.with_name(f".{manifest.name}.part")
        try:
            temp_manifest.write_text(
                json.dumps(
                    sorted(path.name for path in current_paths),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temp_manifest.replace(manifest)
        except OSError as error:
            report["failed"].append(
                {"url": "", "error": f"첨부파일 목록 저장 실패: {error}"}
            )
        finally:
            if temp_manifest.exists():
                try:
                    temp_manifest.unlink()
                except OSError:
                    pass


def safe_path_component(value, fallback):
    text = unquote(str(value or "")).strip()
    text = INVALID_PATH_CHARS.sub("_", text).strip(" .")
    text = re.sub(r"\s+", " ", text)
    if not text:
        text = str(fallback or "파일").strip()
    if text.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        text = f"_{text}"
    return text[:120].rstrip(" .") or "파일"


def _unique_url_attachments(attachments):
    rows = []
    seen = set()
    for attachment in attachments:
        url = str(attachment.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(attachment)
    return rows


def _filename_from_url(url):
    return unquote(Path(urlparse(str(url or "")).path).name)
