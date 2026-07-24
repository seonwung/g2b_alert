"""Application stylesheet built from the shared Figma design tokens."""

from .design_tokens import Colors, Metrics, Typography

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
QFrame[card='true'] {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 11px; }}
QWidget#emailSettingsPanel {{ background: transparent; border: none; }}
QWidget#modalOverlay {{ background: rgba(20, 20, 20, 105); border: none; }}
QWidget#helpTooltipWindow {{ background: transparent; border: none; }}
QFrame#helpTooltipCard {{ background: #FFFFFF; border: 1px solid {Colors.CARD_BORDER}; border-radius: 7px; }}
QLabel#helpTooltipText {{ background: transparent; border: none; color: #5F6670; font-size: 10pt; font-weight: 500; }}
QDialog#smtpTestDialog {{ background: transparent; border: none; }}
QFrame#smtpTestCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 12px; }}
QLabel[dialogTitle='true'] {{ color: {SUB_TEXT}; font-size: 13pt; font-weight: 600; }}
QLabel[dialogSection='true'] {{ color: {SUB_TEXT}; font-size: 11pt; font-weight: 500; }}
QLabel[smtpTestStatus='true'] {{ color: {SUB_TEXT}; font-size: 10pt; font-weight: 500; }}
QLabel[smtpTestStatus='true'][testResult='success'] {{ color: {SUB_TEXT}; }}
QLabel[smtpTestStatus='true'][testResult='error'] {{ color: {DANGER}; }}
QPushButton[modalClose='true'][iconButton='true'] {{ min-width: 18px; max-width: 18px; min-height: 30px; max-height: 30px; padding: 0; border: none; background: transparent; }}
QPushButton[modalClose='true'][iconButton='true']:hover, QPushButton[modalClose='true'][iconButton='true']:pressed, QPushButton[modalClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QDialog#conditionDialog {{ background: transparent; border: none; }}
QFrame#conditionDialogCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 7px; }}
QLabel[conditionCaption='true'] {{ color: {SUB_TEXT}; font-size: 10pt; font-weight: 500; }}
QLabel[conditionFieldLabel='true'] {{ color: #60656D; font-size: 9pt; font-weight: 500; }}
QDialog#conditionDialog QLineEdit, QDialog#conditionDialog QComboBox {{ min-height: 32px; max-height: 32px; padding: 0 10px; border-radius: 6px; font-size: 10pt; }}
QDialog#conditionDialog QCheckBox {{ spacing: 5px; font-size: 9pt; }}
QDialog#conditionDialog QCheckBox::indicator {{ width: 15px; height: 15px; }}
QPushButton[conditionCompact='true'] {{ min-height: 32px; max-height: 32px; padding: 0 12px; border-radius: 6px; font-size: 10pt; }}
QPushButton[conditionClose='true'][iconButton='true'] {{ min-width: 18px; max-width: 18px; min-height: 24px; max-height: 24px; padding: 0; border: none; background: transparent; }}
QPushButton[conditionClose='true'][iconButton='true']:hover, QPushButton[conditionClose='true'][iconButton='true']:pressed, QPushButton[conditionClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QFrame[conditionKeywordChip='true'] {{ background: {PRIMARY_TINT}; border: 0; border-radius: 14px; }}
QFrame[conditionKeywordChip='true'] QLabel {{ color: {TEXT}; font-size: 8pt; font-weight: 600; border: 0; background: transparent; }}
QPushButton[conditionChipRemove='true'][iconButton='true'] {{ min-width: 20px; max-width: 20px; min-height: 22px; max-height: 22px; padding: 0; border: none; background: transparent; }}
QPushButton[conditionChipRemove='true'][iconButton='true']:hover, QPushButton[conditionChipRemove='true'][iconButton='true']:pressed, QPushButton[conditionChipRemove='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QDialog#recipientSelectionDialog {{ background: transparent; border: none; }}
QFrame#recipientSelectionCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 7px; }}
QLabel[recipientCaption='true'] {{ color: {SUB_TEXT}; font-size: 10pt; font-weight: 500; }}
QLabel[recipientTarget='true'] {{ color: {TEXT}; font-size: 9pt; font-weight: 500; }}
QLabel[recipientHint='true'] {{ color: {SUB_TEXT}; font-size: 9pt; font-weight: 500; }}
QDialog#recipientSelectionDialog QCheckBox {{ spacing: 6px; font-size: 9pt; }}
QDialog#recipientSelectionDialog QCheckBox::indicator {{ width: 15px; height: 15px; }}
QFrame[recipientDivider='true'] {{ background: {Colors.BORDER}; border: none; min-width: 1px; max-width: 1px; }}
QPushButton[recipientClose='true'][iconButton='true'] {{ min-width: 18px; max-width: 18px; min-height: 24px; max-height: 24px; padding: 0; border: none; background: transparent; }}
QPushButton[recipientClose='true'][iconButton='true']:hover, QPushButton[recipientClose='true'][iconButton='true']:pressed, QPushButton[recipientClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QPushButton[recipientSave='true'] {{ min-height: 32px; max-height: 32px; padding: 0 12px; border-radius: 6px; font-size: 10pt; }}
QDialog#customContentDialog {{ background: transparent; border: none; }}
QFrame#customContentDialogCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 10px; }}
QPushButton[contentDialogClose='true'][iconButton='true'] {{ min-width: 20px; max-width: 20px; min-height: 30px; max-height: 30px; padding: 0; border: none; background: transparent; }}
QPushButton[contentDialogClose='true'][iconButton='true']:hover, QPushButton[contentDialogClose='true'][iconButton='true']:pressed, QPushButton[contentDialogClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QLabel[historyCaption='true'] {{ color: {SUB_TEXT}; font-size: 9pt; font-weight: 500; }}
QLabel[historyTitle='true'] {{ color: {TEXT}; font-size: 13pt; font-weight: 700; }}
QLabel[historyReference='true'] {{ color: {SUB_TEXT}; font-size: 9pt; font-weight: 500; }}
QScrollArea#historyTimeline, QScrollArea#historyChanges {{ background: transparent; border: none; }}
QLabel[historyConnector='true'] {{ color: #B9C3D2; font-size: 10pt; }}
QPushButton[historyStep='true'] {{ min-width: 82px; max-width: 82px; min-height: 50px; max-height: 50px; padding: 0; color: {SUB_TEXT}; background: #F4F6F9; border: 1px solid {Colors.BORDER}; border-radius: 8px; font-size: 9pt; font-weight: 600; }}
QPushButton[historyStep='true']:hover {{ color: {TEXT}; background: #EDF2FA; border-color: #B6C7E5; }}
QPushButton[historyStep='true']:checked {{ color: #FFFFFF; background: {PRIMARY}; border-color: {PRIMARY}; }}
QLabel[historySummary='true'] {{ color: {TEXT}; font-size: 10pt; font-weight: 700; padding: 3px 2px; }}
QFrame[historyChangeCard='true'] {{ background: #FAFBFD; border: 1px solid {Colors.BORDER}; border-radius: 9px; }}
QLabel[historyChangeBadge='true'] {{ color: {PRIMARY_DARK}; background: {PRIMARY_TINT}; border: none; border-radius: 10px; padding: 3px 8px; font-size: 8pt; font-weight: 700; }}
QLabel[historyChangeBadge='true'][changeKind='attachments'] {{ color: #8A5B10; background: #FFF0C7; }}
QLabel[historyChangeBadge='true'][changeKind='budget_amount'] {{ color: #256340; background: #D9F4EB; }}
QLabel[historyChangeLabel='true'] {{ color: {TEXT}; font-size: 10pt; font-weight: 700; }}
QLabel[historyFileSummary='true'] {{ color: #8A5B10; font-size: 9pt; font-weight: 600; }}
QLabel[historyValueKey='before'] {{ color: {SUB_TEXT}; font-size: 8pt; font-weight: 600; }}
QLabel[historyValueKey='after'] {{ color: {PRIMARY}; font-size: 8pt; font-weight: 700; }}
QLabel[historyValue='before'] {{ color: #7D838C; font-size: 9pt; text-decoration: line-through; }}
QLabel[historyValue='after'] {{ color: {PRIMARY_DARK}; font-size: 9pt; font-weight: 700; }}
QFrame[historyFileDetails='true'] {{ background: #FFFFFF; border: 1px solid {Colors.BORDER}; border-radius: 7px; }}
QLabel[historyFileItem='added'] {{ color: #24784C; font-size: 8pt; }}
QLabel[historyFileItem='removed'] {{ color: #B33A3A; font-size: 8pt; }}
QPushButton[historyFileToggle='true'], QPushButton[historyOriginalToggle='true'] {{ min-height: 28px; max-height: 28px; padding: 0 10px; color: {PRIMARY}; background: transparent; border: 1px solid #BDD0F2; border-radius: 6px; font-size: 8pt; font-weight: 600; }}
QTextBrowser[historyOriginal='true'] {{ background: #F7F8FA; color: #545B66; border: 1px solid {Colors.BORDER}; border-radius: 7px; padding: 10px; font-size: 8pt; }}
QFrame[historyEmptyCard='true'] {{ background: #FAFBFD; border: 1px solid {Colors.BORDER}; border-radius: 9px; }}
QLabel[historyEmptyText='true'] {{ color: {SUB_TEXT}; font-size: 9pt; }}
QDialog#noticeDetailDialog {{ background: transparent; border: none; }}
QFrame#noticeDetailCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 8px; }}
QLabel[noticeCaption='true'] {{ color: {SUB_TEXT}; font-size: 10pt; font-weight: 500; }}
QLabel[noticeTitle='true'] {{ color: {TEXT}; font-size: 11pt; font-weight: 600; }}
QLabel[noticeDetailKey='true'] {{ color: {TEXT}; font-size: 9pt; font-weight: 600; }}
QLabel[noticeDetailValue='true'] {{ color: {TEXT}; font-size: 9pt; font-weight: 500; }}
QPushButton[noticeClose='true'][iconButton='true'] {{ min-width: 18px; max-width: 18px; min-height: 24px; max-height: 24px; padding: 0; border: none; background: transparent; }}
QPushButton[noticeClose='true'][iconButton='true']:hover, QPushButton[noticeClose='true'][iconButton='true']:pressed, QPushButton[noticeClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QPushButton[noticeLink='true'] {{ min-height: 32px; max-height: 32px; padding: 0 12px; border-radius: 7px; font-size: 10pt; }}
QTabWidget#noticeDetailTabs::pane {{ border: none; border-top: 1px solid {Colors.BORDER}; background: transparent; margin: 0; }}
QTabWidget#noticeDetailTabs QTabBar::tab {{ min-height: 36px; max-height: 36px; padding: 0 15px; margin: 0 2px; border: none; background: transparent; color: {SUB_TEXT}; font-size: 9pt; font-weight: 500; }}
QTabWidget#noticeDetailTabs QTabBar::tab:hover {{ color: {TEXT}; background: transparent; }}
QTabWidget#noticeDetailTabs QTabBar::tab:selected {{ color: {PRIMARY}; background: transparent; border: none; font-weight: 600; }}
QTabWidget#noticeDetailTabs QTableWidget, QTabWidget#noticeDetailTabs QTableView {{ font-size: 9pt; }}
QTabWidget#noticeDetailTabs QHeaderView::section {{ min-height: 28px; max-height: 28px; padding: 2px 5px; font-size: 8pt; font-weight: 600; }}
QTableWidget#emailHistoryTable {{ font-size: 9pt; }}
QTableWidget#emailHistoryTable QHeaderView::section {{ min-height: 28px; max-height: 28px; padding: 2px 5px; font-size: 8pt; font-weight: 600; }}
QDialog#appMessageDialog {{ background: transparent; border: none; }}
QFrame#appMessageCard {{ background: {CARD_BG}; border: 1px solid {Colors.CARD_BORDER}; border-radius: 10px; }}
QLabel[messageTitle='true'] {{ color: {TEXT}; font-size: 11pt; font-weight: 600; }}
QLabel[messageBody='true'] {{ color: {TEXT}; font-size: 10pt; font-weight: 500; }}
QLabel[messageBody='true'][messageKind='error'] {{ color: {DANGER}; }}
QPushButton[messageClose='true'][iconButton='true'] {{ min-width: 18px; max-width: 18px; min-height: 26px; max-height: 26px; padding: 0; border: none; background: transparent; }}
QPushButton[messageClose='true'][iconButton='true']:hover, QPushButton[messageClose='true'][iconButton='true']:pressed, QPushButton[messageClose='true'][iconButton='true']:focus {{ border: none; background: transparent; }}
QLabel[role='appTitle'] {{ font-size: 17pt; font-weight: 700; }}
QLabel[role='title'] {{ font-size: 17pt; font-weight: 700; }}
QLabel[role='section'] {{ font-size: 13pt; font-weight: 600; }}
QLabel[muted='true'] {{ color: {SUB_TEXT}; font-size: 10pt; }}
QLabel[fieldLabel='true'] {{ color: #60656D; font-size: 9pt; font-weight: 500; }}
QLabel[cardCaption='true'] {{ color: {SUB_TEXT}; font-size: 10pt; font-weight: 500; }}
QPushButton {{ min-height: {Metrics.CONTROL_HEIGHT - 2}px; max-height: {Metrics.CONTROL_HEIGHT - 2}px; padding: 0 16px; border: 1px solid {NEUTRAL_BORDER}; border-radius: 8px; background: white; font-size: 11pt; font-weight: 600; }}
QPushButton:hover {{ background: #F2F4F7; border-color: #AEB4BC; }}
QPushButton:pressed {{ background: #E8EBEF; }}
QPushButton:focus {{ border: 1px solid {PRIMARY}; }}
QPushButton:disabled {{ color: {Colors.TEXT_DISABLED}; background: {Colors.DISABLED}; border-color: {Colors.DISABLED}; }}
QPushButton[primary='true'] {{ color: white; background: {PRIMARY}; border-color: {PRIMARY}; }}
QPushButton[primary='true']:hover {{ background: {Colors.PRIMARY_HOVER}; border-color: {Colors.PRIMARY_HOVER}; }}
QPushButton[primary='true']:pressed {{ background: {Colors.PRIMARY_PRESSED}; border-color: {Colors.PRIMARY_PRESSED}; }}
QPushButton[danger='true'] {{ color: {DANGER}; background: white; border-color: {DANGER}; }}
QPushButton[danger='true']:hover {{ color: {DANGER}; background: white; border-color: {DANGER}; }}
QPushButton[monitorState='start'] {{ min-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; max-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; padding: 0 8px; font-size: 10pt; color: white; background: {PRIMARY}; border: 1px solid {PRIMARY}; }}
QPushButton[monitorState='start']:hover {{ color: white; background: {Colors.PRIMARY_HOVER}; border-color: {Colors.PRIMARY_HOVER}; }}
QPushButton[monitorState='start']:pressed, QPushButton[monitorState='start']:focus {{ color: white; background: {PRIMARY}; border: 1px solid {PRIMARY}; }}
QPushButton[monitorState='stop'] {{ min-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; max-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; padding: 0 8px; font-size: 10pt; color: {DANGER}; background: white; border: 1px solid {DANGER}; }}
QPushButton[monitorState='stop']:hover, QPushButton[monitorState='stop']:pressed, QPushButton[monitorState='stop']:focus {{ color: {DANGER}; background: white; border: 1px solid {DANGER}; }}
QPushButton[monitorState='busy'] {{ min-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; max-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; padding: 0 8px; font-size: 10pt; color: {Colors.TEXT_DISABLED}; background: {Colors.DISABLED}; border: 1px solid {Colors.DISABLED}; }}
QPushButton[outlinePrimary='true'] {{ color: {PRIMARY}; background: white; border: 1px solid {PRIMARY}; }}
QPushButton[outlinePrimary='true']:hover {{ color: {PRIMARY}; background: {PRIMARY_TINT}; border: 1px solid {PRIMARY}; }}
QPushButton[outlinePrimary='true']:pressed, QPushButton[outlinePrimary='true']:focus {{ color: {PRIMARY}; background: white; border: 1px solid {PRIMARY}; }}
QPushButton[textAction='true'] {{ color: {PRIMARY}; background: transparent; border: none; padding: 0 4px; }}
QPushButton[textAction='true']:hover, QPushButton[textAction='true']:pressed, QPushButton[textAction='true']:focus {{ color: {Colors.PRIMARY_HOVER}; background: transparent; border: none; }}
QPushButton[figmaCompact='true'] {{ min-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; max-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; padding: 0 14px; }}
QPushButton[rowDelete='true'] {{ min-width: 38px; max-width: 38px; min-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; max-height: {Metrics.COMPACT_CONTROL_HEIGHT - 2}px; padding: 0; }}
QPushButton[apiLink='true'] {{ min-height: 38px; max-height: 38px; padding: 0 14px; font-size: 10pt; font-weight: 500; }}
QPushButton[deleteButton='true'] {{ color: {Colors.DELETE_TEXT}; background: {Colors.DELETE_BG}; border-color: {Colors.DELETE_BG}; }}
QPushButton[deleteButton='true']:hover {{ background: {Colors.DELETE_HOVER}; border-color: {Colors.DELETE_HOVER}; }}
QPushButton[iconButton='true'] {{ min-width: 38px; padding: 0; }}
QPushButton[emailLink='true'] {{ min-height: 30px; padding: 0 4px; border: none; background: transparent; color: {PRIMARY}; font-size: 9pt; }}
QPushButton[emailLink='true']:hover, QPushButton[emailLink='true']:pressed, QPushButton[emailLink='true']:focus {{ border: none; background: transparent; color: {Colors.PRIMARY_HOVER}; }}
QFrame[recipientChip='true'] {{ background: {PRIMARY_TINT}; border: none; border-radius: 16px; }}
QFrame[recipientChip='true'] QLabel {{ color: {PRIMARY}; font-size: 9pt; font-weight: 500; border: none; background: transparent; }}
QPushButton[chipRemove='true'] {{ min-width: 24px; max-width: 24px; min-height: 24px; padding: 0; border: none; background: transparent; }}
QPushButton[chipRemove='true']:hover, QPushButton[chipRemove='true']:pressed, QPushButton[chipRemove='true']:focus {{ border: none; background: #C8DAFB; }}
QPushButton[nav='true'] {{ border: none; border-radius: 19px; background: transparent; color: #444444; padding: 0 18px; font-size: 11pt; font-weight: 600; }}
QPushButton[nav='true']:hover {{ border: none; background: transparent; color: {PRIMARY_DARK}; }}
QPushButton[nav='true']:pressed, QPushButton[nav='true']:focus {{ border: none; background: transparent; }}
QPushButton[navSelected='true'], QPushButton[navSelected='true']:hover, QPushButton[navSelected='true']:pressed, QPushButton[navSelected='true']:focus {{ color: {PRIMARY_DARK}; background: {PRIMARY_TINT}; border: none; }}
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{ min-height: {Metrics.CONTROL_HEIGHT - 2}px; max-height: {Metrics.CONTROL_HEIGHT - 2}px; padding: 0 12px; border: 1px solid {NEUTRAL_BORDER}; border-radius: 8px; background: {INPUT_BG}; font-size: 11pt; font-weight: 500; selection-background-color: {PRIMARY}; }}
QTextEdit, QPlainTextEdit {{ min-height: 88px; padding: 10px 12px; border: 1px solid {NEUTRAL_BORDER}; border-radius: 8px; background: {INPUT_BG}; font-size: 11pt; font-weight: 500; selection-background-color: {PRIMARY}; }}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDateEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{ border-color: #AEB4BC; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{ border: 1px solid {PRIMARY}; }}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{ color: {Colors.TEXT_DISABLED}; background: #F1F2F4; border-color: {Colors.BORDER_SOFT}; }}
QLineEdit[apiKeyInput='true'] QToolButton {{ margin: 0; padding: 0; border: none; background: transparent; }}
QComboBox {{ padding-right: 34px; }}
QComboBox:on {{ border-color: {PRIMARY}; background: white; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; border: none; width: 34px; background: transparent; }}
QComboBox::drop-down:hover {{ background: #F3F6FB; }}
QComboBox::down-arrow {{ image: url('{combo_arrow}'); width: 12px; height: 12px; }}
QFrame#figmaComboPopupContainer {{ background: white; border: 1px solid {Colors.BORDER}; border-radius: 8px; }}
QFrame#figmaComboPopupContainer QAbstractItemView {{ background: white; color: {TEXT}; border: none; border-radius: 0; padding: 5px; outline: 0; selection-background-color: {Colors.PRIMARY_TINT}; selection-color: {TEXT}; font-size: 11pt; font-weight: 500; }}
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
QTableWidget#savedBidsTable::item:selected {{ background: {Colors.PRIMARY}; color: #FFFFFF; border-top: 1px solid {Colors.PRIMARY_PRESSED}; border-bottom: 1px solid {Colors.PRIMARY_PRESSED}; }}
QHeaderView::section {{ background: #E6E6E6; color: #666666; border: none; border-right: 1px solid white; padding: 8px; font-weight: 600; }}
QTabWidget, QStackedWidget {{ border: none; background: transparent; }}
QTabWidget::pane {{ border: 0; background: transparent; margin: 0; }}
QTabWidget#settingsTabs::tab-bar {{ left: 24px; }}
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
QDialog {{ background: {CARD_BG}; }}
"""


APP_STYLESHEET = build_stylesheet()
