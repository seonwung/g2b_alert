"""Reusable Qt widgets used across the Figma-derived screens."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QProxyStyle,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QGuiApplication, QPalette

from .design_tokens import Metrics
from .resources import local_icon


class FlowLayout(QLayout):
    """Responsive left-to-right layout that wraps widgets onto new rows."""

    def __init__(
        self,
        parent=None,
        *,
        margin=0,
        horizontal_spacing=8,
        vertical_spacing=8,
    ):
        super().__init__(parent)
        self._items = []
        self._horizontal_spacing = horizontal_spacing
        self._vertical_spacing = vertical_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    def _do_layout(self, rect, *, test_only):
        margins = self.contentsMargins()
        content_rect = rect.adjusted(
            margins.left(),
            margins.top(),
            -margins.right(),
            -margins.bottom(),
        )
        x = content_rect.x()
        y = content_rect.y()
        line_height = 0

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._horizontal_spacing
            if (
                line_height > 0
                and next_x - self._horizontal_spacing > content_rect.right() + 1
            ):
                x = content_rect.x()
                y += line_height + self._vertical_spacing
                next_x = x + item_size.width() + self._horizontal_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())

        return (
            y
            + line_height
            - rect.y()
            + margins.bottom()
        )


class HelpIcon(QLabel):
    """Help icon with an application-styled explanatory hover card."""

    def __init__(self, description, parent=None, *, icon_size=14, width=330):
        super().__init__(parent)
        self.description = str(description)
        self.popup_width = int(width)
        self._popup = None
        self.setPixmap(local_icon("help.svg").pixmap(icon_size, icon_size))
        self.setFixedSize(icon_size, icon_size)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)

    def enterEvent(self, event):
        self._show_popup()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_popup()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self._hide_popup()
        super().hideEvent(event)

    def _ensure_popup(self):
        if self._popup is not None:
            return
        self._popup = QFrame(
            self.window(),
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint,
        )
        self._popup.setObjectName("helpTooltipPopup")
        self._popup.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )
        layout = QVBoxLayout(self._popup)
        layout.setContentsMargins(14, 11, 14, 11)
        text = QLabel(self.description)
        text.setObjectName("helpTooltipText")
        text.setWordWrap(True)
        text.setFixedWidth(self.popup_width)
        layout.addWidget(text)
        shadow = QGraphicsDropShadowEffect(self._popup)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(20, 25, 32, 50))
        self._popup.setGraphicsEffect(shadow)

    def _show_popup(self):
        if not self.description:
            return
        self._ensure_popup()
        self._popup.adjustSize()
        position = self.mapToGlobal(QPoint(-18, self.height() + 8))
        screen = QGuiApplication.screenAt(position)
        if screen is not None:
            available = screen.availableGeometry()
            x = min(
                max(position.x(), available.left() + 8),
                available.right() - self._popup.width() - 8,
            )
            y = position.y()
            if y + self._popup.height() > available.bottom() - 8:
                y = (
                    self.mapToGlobal(QPoint(0, 0)).y()
                    - self._popup.height()
                    - 8
                )
            position = QPoint(x, max(available.top() + 8, y))
        self._popup.move(position)
        self._popup.show()
        self._popup.raise_()

    def _hide_popup(self):
        if self._popup is not None:
            self._popup.hide()


class AsteriskPasswordStyle(QProxyStyle):
    """Force password fields to use an asterisk instead of the OS mask glyph."""

    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.StyleHint.SH_LineEdit_PasswordCharacter:
            return ord("*")
        return super().styleHint(hint, option, widget, return_data)


class AsteriskPasswordLineEdit(QLineEdit):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._asterisk_style = AsteriskPasswordStyle()
        self._trailing_action_inset = 0
        self.setStyle(self._asterisk_style)
        self.setEchoMode(QLineEdit.EchoMode.Password)

    def set_trailing_action_inset(self, inset):
        self._trailing_action_inset = max(0, int(inset))
        self.setTextMargins(0, 0, self._trailing_action_inset + 24, 0)
        self._position_trailing_actions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_trailing_actions()

    def _position_trailing_actions(self):
        if not self._trailing_action_inset:
            return
        for action_button in self.findChildren(QToolButton):
            action_button.move(
                max(
                    0,
                    self.width()
                    - self._trailing_action_inset
                    - action_button.width(),
                ),
                action_button.y(),
            )


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def button(
    text: str,
    callback=None,
    *,
    primary=False,
    danger=False,
    delete=False,
    height=Metrics.CONTROL_HEIGHT,
    icon: str = "",
) -> QPushButton:
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
        # QPushButton.clicked emits a bool. Controller actions such as
        # start(enable_all=True) and stop(disable_all=True) have optional
        # parameters, so connecting them directly replaces True with the
        # emitted False and accidentally disables the bulk operation.
        result.clicked.connect(
            lambda _checked=False, handler=callback: handler()
        )
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
        self.layout.setContentsMargins(
            Metrics.CARD_PADDING,
            Metrics.CARD_PADDING,
            Metrics.CARD_PADDING,
            Metrics.CARD_PADDING,
        )
        self.layout.setSpacing(Metrics.CARD_SPACING)
        if title:
            label = QLabel(title)
            label.setProperty("role", "section")
            self.layout.addWidget(label)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(28, 32, 38, 18))
        self.setGraphicsEffect(shadow)


class DraggableDialog(QDialog):
    """Frameless dialog that can be moved by dragging its title region."""

    DRAG_REGION_HEIGHT = 72

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset = None

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.position().y() <= self.DRAG_REGION_HEIGHT
        ):
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class AppMessageDialog(DraggableDialog):
    """Application-owned replacement for native QMessageBox windows."""

    def __init__(
        self,
        title,
        message,
        *,
        kind="info",
        question=False,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("appMessageDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(408, 220)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("appMessageCard")
        card.layout.setContentsMargins(20, 16, 20, 18)
        outer.addWidget(card)

        header = QHBoxLayout()
        header.setSpacing(7)
        icon = QLabel()
        icon.setPixmap(local_icon("notice.svg").pixmap(16, 16))
        header.addWidget(icon)
        heading = QLabel(title)
        heading.setProperty("messageTitle", True)
        header.addWidget(heading)
        header.addStretch()
        close_button = button(
            "",
            self.reject,
            height=26,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("messageClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        card.layout.addLayout(header)

        body = QLabel(str(message))
        body.setProperty("messageBody", True)
        body.setProperty("messageKind", kind)
        body.setWordWrap(True)
        body.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        card.layout.addWidget(body, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        if question:
            footer.addWidget(button("취소", self.reject, height=34))
        confirm = button(
            "확인",
            self.accept,
            primary=True,
            height=34,
        )
        confirm.setFixedWidth(68)
        footer.addWidget(confirm)
        card.layout.addLayout(footer)


def show_app_message(parent, title, message, *, kind="info", question=False):
    """Show a styled modal and return True when its confirm action is used."""
    modal_parent = parent.window() if parent is not None else None
    overlay = None
    if modal_parent is not None:
        overlay = QWidget(modal_parent)
        overlay.setObjectName("modalOverlay")
        overlay.setGeometry(modal_parent.rect())
        overlay.show()
        overlay.raise_()
    dialog = AppMessageDialog(
        title,
        message,
        kind=kind,
        question=question,
        parent=modal_parent,
    )
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        if overlay is not None:
            overlay.deleteLater()


class Page(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            Metrics.PAGE_HORIZONTAL_PADDING,
            Metrics.PAGE_VERTICAL_PADDING,
            Metrics.PAGE_HORIZONTAL_PADDING,
            Metrics.PAGE_VERTICAL_PADDING,
        )
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
        self._prepare_popup_container()

    def _prepare_popup_container(self):
        """Prevent Windows' private popup frame from showing dark corners."""
        if self.count():
            metrics = self.view().fontMetrics()
            content_width = max(
                metrics.horizontalAdvance(self.itemText(index))
                for index in range(self.count())
            ) + 44
            available_width = max(120, self.screen().availableGeometry().width() - 32)
            self.view().setMinimumWidth(
                min(max(self.width(), content_width), available_width)
            )
        popup = self.view().window()
        popup.setObjectName("figmaComboPopupContainer")
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setAutoFillBackground(True)
        palette = popup.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        popup.setPalette(palette)

    def showPopup(self):
        self._prepare_popup_container()
        super().showPopup()


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
