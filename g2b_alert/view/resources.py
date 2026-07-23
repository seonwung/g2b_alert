"""Local UI asset and bundled font loading."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
ICON_ROOT = ASSET_ROOT / "icons"
PRETENDARD_ROOT = ASSET_ROOT / "Pretendard-1.3.9" / "public" / "static"


def asset_path(*parts: str) -> Path:
    return ASSET_ROOT.joinpath(*parts)


@lru_cache(maxsize=None)
def local_icon(name: str) -> QIcon:
    path = ICON_ROOT / name
    return QIcon(str(path)) if path.is_file() else QIcon()


def qss_url(*parts: str) -> str:
    return asset_path(*parts).resolve().as_posix()


def load_pretendard() -> str:
    """Register every weight used by Figma and make Pretendard application-wide."""
    loaded_families: list[str] = []
    for filename in (
        "Pretendard-Regular.otf",
        "Pretendard-Medium.otf",
        "Pretendard-SemiBold.otf",
        "Pretendard-Bold.otf",
    ):
        font_id = QFontDatabase.addApplicationFont(str(PRETENDARD_ROOT / filename))
        if font_id >= 0:
            loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
    family = next((name for name in loaded_families if "Pretendard" in name), "Pretendard")
    # Use a point-sized application font. Pixel-sized fonts report pointSize()
    # as -1, which makes some native Qt controls call setPointSize(-1).
    QApplication.setFont(QFont(family, 11))
    return family
