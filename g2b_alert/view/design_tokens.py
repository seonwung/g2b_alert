"""Shared visual tokens derived from the supplied Figma reference screens."""


class Colors:
    APP_BACKGROUND = "#F3F4F6"
    CARD = "#FFFFFF"
    CARD_SUBTLE = "#F8FAFD"
    TEXT = "#171717"
    TEXT_SECONDARY = "#767676"
    TEXT_DISABLED = "#A7A7A7"
    BORDER = "#D9D9D9"
    BORDER_SOFT = "#E9EDF3"
    PRIMARY = "#5487E4"
    PRIMARY_HOVER = "#4678D2"
    PRIMARY_PRESSED = "#3868BC"
    PRIMARY_TINT = "#DAE7FF"
    PRIMARY_TEXT = "#154CB2"
    DISABLED = "#DDE3EC"
    STOP = "#F93D3D"
    STOP_HOVER = "#E83333"
    DELETE_BG = "#ECECEC"
    DELETE_HOVER = "#DCDCDC"
    DELETE_TEXT = "#666666"
    LOG_BACKGROUND = "#303030"
    LOG_TEXT = "#F7F7F7"
    LOG_TIME = "#C9CDD3"
    LOG_WARNING = "#FFD166"
    LOG_ERROR = "#FF7B7B"
    LOG_EMAIL = "#91C6FF"
    STAGE_PRE_SPEC = "#D9F4EB"
    STAGE_BID = "#DCEAFF"
    STAGE_OPENING = "#FFF0C7"
    STAGE_AWARD = "#ECE1FF"
    STAGE_CONTRACT = "#DDF2D6"
    STAGE_CANCELLED = "#ECEDEF"


class Typography:
    FAMILY = "Pretendard"
    PAGE_TITLE = 24
    SECTION_TITLE = 18
    MENU = 15
    BUTTON = 14
    BODY = 14
    INPUT = 14
    CAPTION = 12
    LOG = 13
    MEDIUM = 500
    SEMIBOLD = 600
    BOLD = 700


class Spacing:
    XS, SM, MD, LG, XL, XXL, XXXL = 4, 8, 12, 16, 20, 24, 32


class Radius:
    SMALL, CONTROL, CARD = 6, 8, 11


STAGE_COLORS = {
    "사전규격": Colors.STAGE_PRE_SPEC,
    "입찰공고": Colors.STAGE_BID,
    "개찰결과": Colors.STAGE_OPENING,
    "낙찰결과": Colors.STAGE_AWARD,
    "계약체결": Colors.STAGE_CONTRACT,
    "계약완료": Colors.STAGE_CONTRACT,
    "유찰·취소": Colors.STAGE_CANCELLED,
}
