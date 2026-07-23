"""Application stylesheet built from the shared Figma design tokens."""

from .design_tokens import Colors, Typography

APP_BG = Colors.APP_BACKGROUND
CARD_BG = Colors.CARD
PRIMARY = Colors.PRIMARY
PRIMARY_DARK = Colors.PRIMARY_TEXT
PRIMARY_TINT = Colors.PRIMARY_TINT
SUCCESS = "#2F9E72"
DANGER = Colors.STOP
WARNING = "#E98B24"
GRAY = Colors.TEXT_SECONDARY
DISABLED_BLUE = "#AFC5ED"
STOP_RED = DANGER
TEXT = Colors.TEXT
SUB_TEXT = Colors.TEXT_SECONDARY
BORDER = Colors.BORDER_SOFT
NEUTRAL_BORDER = Colors.BORDER
INPUT_BG = Colors.CARD
LOG_BG = Colors.LOG_BACKGROUND
LOG_TEXT = Colors.LOG_TEXT
STATUS_BG = Colors.CARD
FONT_FAMILY = Typography.FAMILY
FONT = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")


def build_stylesheet(check_off="", check_on="", combo_arrow=""):
    return f"""
* {{ font-family: '{FONT_FAMILY}', 'Malgun Gothic', sans-serif; font-size: 11pt; font-weight: 500; color: {TEXT}; outline: none; }}
QMainWindow, QWidget#appRoot {{ background: {APP_BG}; }}
QFrame#header, QFrame#subbar {{ background: transparent; border: none; }}
QFrame[card='true'] {{ background: {CARD_BG}; border: 1px solid {Colors.BORDER_SOFT}; border-radius: 11px; }}
QLabel[role='appTitle'] {{ font-size: 17pt; font-weight: 700; }}
QLabel[role='title'] {{ font-size: 17pt; font-weight: 700; }}
QLabel[role='section'] {{ font-size: 13pt; font-weight: 600; }}
QLabel[muted='true'] {{ color: {SUB_TEXT}; font-size: 10pt; }}
QPushButton {{ min-height: 38px; padding: 0 16px; border: 1px solid {NEUTRAL_BORDER}; border-radius: 8px; background: white; font-size: 11pt; font-weight: 600; }}
QPushButton:hover {{ background: #F2F4F7; border-color: #AEB4BC; }}
QPushButton:pressed {{ background: #E8EBEF; }}
QPushButton:focus {{ border: 1px solid {PRIMARY}; }}
QPushButton:disabled {{ color: {Colors.TEXT_DISABLED}; background: {Colors.DISABLED}; border-color: {Colors.DISABLED}; }}
QPushButton[primary='true'] {{ color: white; background: {PRIMARY}; border-color: {PRIMARY}; }}
QPushButton[primary='true']:hover {{ background: {Colors.PRIMARY_HOVER}; border-color: {Colors.PRIMARY_HOVER}; }}
QPushButton[primary='true']:pressed {{ background: {Colors.PRIMARY_PRESSED}; border-color: {Colors.PRIMARY_PRESSED}; }}
QPushButton[danger='true'] {{ color: {DANGER}; background: white; border-color: {DANGER}; }}
QPushButton[danger='true']:hover {{ color: white; background: {Colors.STOP_HOVER}; border-color: {Colors.STOP_HOVER}; }}
QPushButton[deleteButton='true'] {{ color: {Colors.DELETE_TEXT}; background: {Colors.DELETE_BG}; border-color: {Colors.DELETE_BG}; }}
QPushButton[deleteButton='true']:hover {{ background: {Colors.DELETE_HOVER}; border-color: {Colors.DELETE_HOVER}; }}
QPushButton[iconButton='true'] {{ min-width: 38px; padding: 0; }}
QPushButton[nav='true'] {{ border: none; border-radius: 19px; color: #444444; padding: 0 18px; font-size: 11pt; font-weight: 600; }}
QPushButton[nav='true']:focus {{ border: none; }}
QPushButton[navSelected='true'] {{ color: {PRIMARY_DARK}; background: {PRIMARY_TINT}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{ min-height: 38px; padding: 0 12px; border: 1px solid {NEUTRAL_BORDER}; border-radius: 8px; background: {INPUT_BG}; font-size: 11pt; font-weight: 500; selection-background-color: {PRIMARY}; }}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{ border-color: #AEB4BC; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{ border: 1px solid {PRIMARY}; }}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{ color: {Colors.TEXT_DISABLED}; background: #F1F2F4; border-color: {Colors.BORDER_SOFT}; }}
QComboBox {{ padding-right: 34px; }}
QComboBox:on {{ border-color: {PRIMARY}; background: white; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; border: none; width: 34px; background: transparent; }}
QComboBox::drop-down:hover {{ background: #F3F6FB; }}
QComboBox::down-arrow {{ image: url('{combo_arrow}'); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: white; color: {TEXT}; border: 1px solid {Colors.BORDER}; border-radius: 8px; padding: 5px; outline: 0; selection-background-color: {Colors.PRIMARY_TINT}; selection-color: {TEXT}; font-size: 11pt; font-weight: 500; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; height: 0; border: none; }}
QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down {{ border: none; width: 34px; background: transparent; }}
QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{ image: url('{combo_arrow}'); width: 12px; height: 12px; }}
QCheckBox {{ spacing: 7px; font-size: 11pt; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QCheckBox::indicator:unchecked {{ image: url('{check_off}'); }}
QCheckBox::indicator:checked {{ image: url('{check_on}'); }}
QRadioButton {{ spacing: 7px; font-size: 11pt; }}
QRadioButton::indicator {{ width: 18px; height: 18px; }}
QRadioButton::indicator:unchecked {{ image: url('{check_off}'); }}
QRadioButton::indicator:checked {{ image: url('{check_on}'); }}
QTableWidget, QTableView {{ background: white; border: none; gridline-color: #ECECEC; alternate-background-color: #FAFBFD; selection-background-color: #CFE0FF; selection-color: {TEXT}; font-size: 10pt; }}
QHeaderView::section {{ background: #E6E6E6; color: #666666; border: none; border-right: 1px solid white; padding: 8px; font-weight: 600; }}
QTabWidget, QStackedWidget {{ border: none; background: transparent; }}
QTabWidget::pane {{ border: 0; background: transparent; margin: 0; }}
QTabBar {{ background: transparent; border: 0; qproperty-drawBase: 0; }}
QTabBar::tab {{ min-height: 42px; padding: 0 20px; margin: 0 2px; border: 0; background: transparent; color: {SUB_TEXT}; font-size: 11pt; font-weight: 600; }}
QTabBar::tab:hover {{ color: {TEXT}; background: #F1F3F6; border-radius: 8px; }}
QTabBar::tab:selected {{ color: {PRIMARY}; background: transparent; border: 0; font-weight: 600; }}
QScrollArea, QScrollArea > QWidget > QWidget, QAbstractScrollArea::viewport {{ border: none; background: transparent; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #D9D9D9; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #D9D9D9; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QTextBrowser[logView='true'] {{ background: {LOG_BG}; color: {LOG_TEXT}; border: 0; border-radius: 10px; padding: 16px; font-size: 10pt; font-weight: 500; }}
QFrame[logCard='true'] {{ background: {LOG_BG}; border: 0; border-radius: 11px; }}
QDialog, QMessageBox {{ background: {CARD_BG}; }}
"""


APP_STYLESHEET = build_stylesheet()
