"""Reusable presentation components for the DengLin downloader UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.theme import Colors, Spacing, button_style, card_style, font


class PageHeader(QWidget):
    """Consistent page title and optional subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setFont(font(18, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {Colors.TEXT};")

        self.subtitle_label = QLabel()
        self.subtitle_label.setFont(font(10))
        self.subtitle_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        self.subtitle_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        self.set_text(title, subtitle)

    def set_text(self, title: str, subtitle: str = "") -> None:
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))


class SidebarStepItem(QWidget):
    """Step indicator for the wizard sidebar."""

    _STATE_COLORS = {
        "pending": (Colors.SIDEBAR_CARD, Colors.SIDEBAR_MUTED, Colors.SIDEBAR_MUTED),
        "current": (Colors.PRIMARY, Colors.SURFACE, Colors.SURFACE),
        "done": (Colors.SUCCESS, Colors.SURFACE, Colors.SURFACE),
        "error": (Colors.ERROR, Colors.SURFACE, Colors.SURFACE),
    }

    def __init__(self, number: int, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.number = number
        self._state = "pending"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.badge = QLabel(str(number))
        self.badge.setFixedSize(26, 26)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFont(font(10, QFont.Weight.Bold))

        self.title_label = QLabel(title)
        self.title_label.setFont(font(10, QFont.Weight.Bold))

        layout.addWidget(self.badge)
        layout.addWidget(self.title_label, 1)
        self.set_state("pending")

    def set_state(self, state: str) -> None:
        if state not in self._STATE_COLORS:
            state = "pending"
        self._state = state
        bg, fg, title_color = self._STATE_COLORS[state]
        self.badge.setText("✓" if state == "done" else str(self.number))
        self.badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 13px;"
        )
        self.title_label.setStyleSheet(f"color: {title_color};")


class SelectionCardButton(QPushButton):
    """Checkable card-style button for choosing an option."""

    def __init__(
        self, title: str, description: str = "", parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(68)
        self.setText(title if not description else f"{title}\n{description}")
        self.setFont(font(10, QFont.Weight.Bold))
        self.toggled.connect(self._update_style)
        self._update_style()

    def _update_style(self) -> None:
        border = Colors.PRIMARY if self.isChecked() else Colors.BORDER
        background = Colors.PRIMARY_SOFT if self.isChecked() else Colors.SURFACE
        text = Colors.PRIMARY if self.isChecked() else Colors.TEXT
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {background};
                color: {text};
                border: 1px solid {border};
                border-radius: {Spacing.RADIUS}px;
                padding: {Spacing.CARD}px;
                text-align: left;
                font-family: {font(10, QFont.Weight.Bold).family()};
            }}
            QPushButton:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._update_style()


class SegmentedControl(QWidget):
    """A compact exclusive group of checkable buttons."""

    def __init__(
        self, options: list[tuple[str, str]], parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for key, label in options:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFont(font(10, QFont.Weight.Bold))
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SURFACE};
                    color: {Colors.TEXT_MUTED};
                    border: 1px solid {Colors.BORDER};
                    border-radius: {Spacing.RADIUS}px;
                    padding: 8px 14px;
                }}
                QPushButton:hover {{
                    border-color: {Colors.BORDER_HOVER};
                    color: {Colors.TEXT};
                }}
                QPushButton:checked {{
                    background-color: {Colors.PRIMARY_SOFT};
                    border-color: {Colors.PRIMARY};
                    color: {Colors.PRIMARY};
                }}
            """)
            self.group.addButton(button)
            self.buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)

    def set_checked(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class FooterActions(QWidget):
    """Shared footer navigation buttons."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.back_btn = QPushButton("上一步")
        self.back_btn.setFont(font(10))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet(button_style("secondary"))

        self.next_btn = QPushButton("下一步")
        self.next_btn.setFont(font(10, QFont.Weight.Bold))
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet(button_style("primary"))

        layout.addStretch(1)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.next_btn)


class ElidedLabel(QLabel):
    """Label that keeps its full text in the tooltip and elides in the middle."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full_text = ""
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self._update_elided_text()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self) -> None:
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(
            self._full_text, Qt.TextElideMode.ElideMiddle, self.width()
        )
        QLabel.setText(self, elided)


def panel() -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setStyleSheet(card_style().replace("QWidget#panel", "QFrame#panel"))
    return frame
