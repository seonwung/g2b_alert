"""Reusable Qt widgets used across the Figma-derived screens."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor

from .resources import local_icon


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def button(text: str, callback=None, *, primary=False, danger=False, delete=False, height=40, icon: str = "") -> QPushButton:
    result = QPushButton(text)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    result.setFixedHeight(height)
    if icon:
        result.setIcon(local_icon(icon))
        result.setIconSize(QSize(16, 16))
    if primary:
        result.setProperty("primary", True)
    if danger:
        result.setProperty("danger", True)
    if delete:
        result.setProperty("deleteButton", True)
    if not text:
        result.setProperty("iconButton", True)
    if callback:
        result.clicked.connect(callback)
    return result


def muted(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", True)
    label.setWordWrap(True)
    return label


class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(12)
        if title:
            label = QLabel(title)
            label.setProperty("role", "section")
            self.layout.addWidget(label)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(17)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(52, 93, 168, 20))
        self.setGraphicsEffect(shadow)


class Page(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 24, 40, 24)
        self.layout.setSpacing(16)


class FigmaComboBox(QComboBox):
    """Combo box with a fully styled popup and predictable Figma row sizing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMaxVisibleItems(10)
        self.view().setUniformItemSizes(True)
        self.view().setSpacing(0)
        self.view().setTextElideMode(Qt.TextElideMode.ElideRight)
        self.view().setStyleSheet(
            "QListView::item { min-height: 38px; padding: 0 10px; border: 0; }"
            "QListView::item:hover { background: #F1F5FC; }"
            "QListView::item:selected { background: #DAE7FF; color: #171717; }"
            "QListView::item:disabled { color: #A7A7A7; background: #F1F2F4; }"
        )


def setup_table(table: QTableWidget, headers: list[str], widths: list[int] | None = None) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if widths:
        for index, width in enumerate(widths):
            table.setColumnWidth(index, width)
    table.horizontalHeader().setStretchLastSection(True)


def labeled_row(label_text: str, widget: QWidget, hint: str = "") -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    label = QLabel(label_text)
    label.setMinimumWidth(105)
    label.setStyleSheet("font-weight: 600")
    layout.addWidget(label)
    layout.addWidget(widget, 1)
    if hint:
        hint_label = muted(hint)
        layout.addWidget(hint_label)
    return container
