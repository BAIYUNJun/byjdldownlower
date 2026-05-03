"""Shared theme tokens for the DengLin downloader UI."""

from __future__ import annotations

from PyQt6.QtGui import QFont


FONT_FAMILY = "Microsoft YaHei, Segoe UI, Arial, sans-serif"
FONT_NAME = "Microsoft YaHei"


class Colors:
    SIDEBAR = "#0F172A"
    SIDEBAR_MUTED = "#94A3B8"
    SIDEBAR_CARD = "#1E293B"
    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_PRESSED = "#1E40AF"
    PRIMARY_SOFT = "#EFF6FF"
    PAGE_BG = "#F6F8FB"
    SURFACE = "#FFFFFF"
    SURFACE_MUTED = "#F8FAFC"
    BORDER = "#D8DEE8"
    BORDER_HOVER = "#AEB8C7"
    TEXT = "#111827"
    TEXT_MUTED = "#64748B"
    DISABLED_BG = "#E5E7EB"
    DISABLED_TEXT = "#9CA3AF"
    SUCCESS = "#16A34A"
    ERROR = "#DC2626"
    LOG_BG = "#111827"
    LOG_TEXT = "#D1D5DB"


class Spacing:
    PAGE_X = 36
    PAGE_Y = 30
    SECTION = 22
    FIELD = 10
    CARD = 14
    RADIUS = 8


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return the default UI font with a consistent family and weight."""
    return QFont(FONT_NAME, size, weight)


def button_style(kind: str = "primary") -> str:
    """Return a shared QPushButton stylesheet."""
    if kind == "secondary":
        return f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Spacing.RADIUS}px;
                padding: 8px 18px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{
                border-color: {Colors.BORDER_HOVER};
                background-color: {Colors.SURFACE_MUTED};
            }}
            QPushButton:pressed {{
                background-color: {Colors.DISABLED_BG};
            }}
            QPushButton:disabled {{
                color: {Colors.DISABLED_TEXT};
                background-color: {Colors.DISABLED_BG};
                border-color: {Colors.DISABLED_BG};
            }}
        """

    background = Colors.SUCCESS if kind == "success" else Colors.PRIMARY
    hover = Colors.SUCCESS if kind == "success" else Colors.PRIMARY_HOVER
    pressed = Colors.SUCCESS if kind == "success" else Colors.PRIMARY_PRESSED

    return f"""
        QPushButton {{
            background-color: {background};
            color: {Colors.SURFACE};
            border: none;
            border-radius: {Spacing.RADIUS}px;
            padding: 8px 18px;
            font-family: {FONT_FAMILY};
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            color: {Colors.DISABLED_TEXT};
            background-color: {Colors.DISABLED_BG};
        }}
    """


def input_style() -> str:
    """Return shared styling for QLineEdit and QComboBox controls."""
    return f"""
        QLineEdit, QComboBox {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {Spacing.RADIUS}px;
            padding: 7px 10px;
            font-family: {FONT_FAMILY};
        }}
        QLineEdit:hover, QComboBox:hover {{
            border-color: {Colors.BORDER_HOVER};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: {Colors.PRIMARY};
        }}
        QLineEdit:disabled, QComboBox:disabled {{
            color: {Colors.DISABLED_TEXT};
            background-color: {Colors.DISABLED_BG};
            border-color: {Colors.DISABLED_BG};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            selection-background-color: {Colors.PRIMARY_SOFT};
            selection-color: {Colors.PRIMARY};
            outline: none;
        }}
    """


def card_style() -> str:
    """Return shared panel styling for QWidget#panel."""
    return f"""
        QWidget#panel {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: {Spacing.RADIUS}px;
        }}
    """
