# Branded Control Console UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the PyQt6 downloader UI as a DengLin branded control console with a left step sidebar, reusable theme/components, clearer page layouts, and fixes for the known version-combo and download-progress issues.

**Architecture:** Keep the existing four-page wizard and signal flow, but move the shell layout into `WizardWindow` and move visual primitives into `theme.py` and `components.py`. Page files remain responsible for page-specific state and worker wiring; reusable components own styling and small presentation behavior only.

**Tech Stack:** Python 3.9+, PyQt6, existing QThread workers, Qt stylesheet strings, `python3 -m py_compile`, offscreen Qt screenshot verification.

---

## File Structure

- Create `downloader/ui/theme.py`: color tokens, spacing constants, font helpers, shared stylesheet functions.
- Create `downloader/ui/components.py`: `PageHeader`, `SidebarStepItem`, `SelectionCardButton`, `SegmentedControl`, `FooterActions`, `ElidedLabel`, and small helper functions.
- Modify `downloader/ui/wizard.py`: replace top step bar with two-column shell, left brand sidebar, page navigation state, and sidebar summary.
- Modify `downloader/ui/welcome_page.py`: rebuild connection form using shared page header and footer action styling.
- Modify `downloader/ui/config_page.py`: replace local card button classes with shared components, add safer version selection state, keep existing worker wiring.
- Modify `downloader/ui/mode_selection_page.py`: restyle preset cards, improve summary and custom file labels, preserve selection logic.
- Modify `downloader/ui/download_page.py`: restructure file list, directory row, progress rows, log, task summary, and remove duplicate `_on_file_completed`.
- Modify `downloader/main.py`: reduce global stylesheet to base controls so component styles are not fighting global styles.
- Create `docs/superpowers/plans/scripts/render_branded_ui.py`: local verification helper that renders representative pages to `/private/tmp/byjdldown_branded_ui`.

---

### Task 1: Add Theme Tokens And Shared Components

**Files:**
- Create: `downloader/ui/theme.py`
- Create: `downloader/ui/components.py`
- Verify: `python3 -m py_compile downloader/ui/theme.py downloader/ui/components.py`
- Commit: `feat: add shared ui theme components`

- [ ] **Step 1: Create `downloader/ui/theme.py`**

Use `apply_patch` to add:

```python
"""Shared UI theme tokens for the DengLin downloader."""

from __future__ import annotations

from PyQt6.QtGui import QFont


FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif'
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
    return QFont(FONT_NAME, size, weight)


def button_style(kind: str = "primary") -> str:
    if kind == "secondary":
        return f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                border-color: {Colors.BORDER_HOVER};
                background-color: {Colors.SURFACE_MUTED};
            }}
            QPushButton:disabled {{
                color: {Colors.DISABLED_TEXT};
                background-color: {Colors.DISABLED_BG};
                border-color: {Colors.DISABLED_BG};
            }}
        """
    if kind == "success":
        return f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{ background-color: #15803D; }}
            QPushButton:disabled {{
                color: white;
                background-color: {Colors.DISABLED_TEXT};
            }}
        """
    return f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 18px;
        }}
        QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}
        QPushButton:pressed {{ background-color: {Colors.PRIMARY_PRESSED}; }}
        QPushButton:disabled {{
            color: white;
            background-color: {Colors.DISABLED_TEXT};
        }}
    """


def input_style() -> str:
    return f"""
        QLineEdit, QComboBox {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: 8px;
            padding: 7px 10px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: {Colors.PRIMARY};
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            selection-background-color: {Colors.PRIMARY_SOFT};
            selection-color: {Colors.TEXT};
        }}
    """


def card_style() -> str:
    return f"""
        QWidget#panel {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: 10px;
        }}
    """
```

- [ ] **Step 2: Create `downloader/ui/components.py`**

Use `apply_patch` to add:

```python
"""Reusable UI components for the DengLin downloader."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.theme import Colors, button_style, font


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setFont(font(20, weight=self.title_label.font().Weight.Bold))
        self.title_label.setStyleSheet(f"color: {Colors.TEXT};")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setFont(font(10))
        self.subtitle_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        self.subtitle_label.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_label)

    def set_text(self, title: str, subtitle: str = ""):
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))


class SidebarStepItem(QWidget):
    def __init__(self, number: int, title: str, parent=None):
        super().__init__(parent)
        self.number = number
        self.title = title
        self.state = "pending"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.badge = QLabel(str(number))
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(26, 26)
        self.badge.setFont(font(10, QFontMetrics(QLabel().font()).font().Weight.Bold))
        layout.addWidget(self.badge)

        self.label = QLabel(title)
        self.label.setFont(font(10))
        layout.addWidget(self.label, 1)

        self.set_state("pending")

    def set_state(self, state: str):
        self.state = state
        if state == "current":
            bg = Colors.PRIMARY
            badge_bg = "white"
            badge_fg = Colors.PRIMARY
            text = "white"
        elif state == "done":
            bg = "transparent"
            badge_bg = Colors.PRIMARY
            badge_fg = "white"
            text = "#DBEAFE"
        elif state == "error":
            bg = "rgba(220, 38, 38, 0.16)"
            badge_bg = Colors.ERROR
            badge_fg = "white"
            text = "white"
        else:
            bg = "transparent"
            badge_bg = Colors.SIDEBAR_CARD
            badge_fg = Colors.SIDEBAR_MUTED
            text = Colors.SIDEBAR_MUTED

        self.setStyleSheet(f"""
            SidebarStepItem {{
                background-color: {bg};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text};
            }}
        """)
        self.badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            border-radius: 13px;
        """)


class SelectionCardButton(QPushButton):
    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.setText(f"{title}\n{description}" if description else title)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(58)
        self.setFont(font(10))
        self.toggled.connect(self._update_style)
        self._update_style()

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY_SOFT};
                    color: {Colors.TEXT};
                    border: 2px solid {Colors.PRIMARY};
                    border-radius: 10px;
                    text-align: center;
                    padding: 8px 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SURFACE};
                    color: {Colors.TEXT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 10px;
                    text-align: center;
                    padding: 8px 10px;
                }}
                QPushButton:hover {{
                    border-color: {Colors.BORDER_HOVER};
                    background-color: {Colors.SURFACE_MUTED};
                }}
                QPushButton:disabled {{
                    color: {Colors.DISABLED_TEXT};
                    background-color: {Colors.DISABLED_BG};
                    border-color: {Colors.DISABLED_BG};
                }}
            """)


class SegmentedControl(QWidget):
    def __init__(self, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for key, label in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SURFACE};
                    color: {Colors.TEXT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 8px;
                    padding: 7px 18px;
                }}
                QPushButton:checked {{
                    background-color: {Colors.PRIMARY_SOFT};
                    color: {Colors.PRIMARY};
                    border: 2px solid {Colors.PRIMARY};
                }}
            """)
            self.group.addButton(btn)
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch(1)

    def set_checked(self, key: str):
        self.buttons[key].setChecked(True)


class FooterActions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)
        self.back_btn = QPushButton("上一步")
        self.back_btn.setMinimumSize(120, 40)
        self.back_btn.setStyleSheet(button_style("secondary"))
        self.next_btn = QPushButton("下一步")
        self.next_btn.setMinimumSize(128, 40)
        self.next_btn.setStyleSheet(button_style("primary"))
        layout.addStretch(1)
        layout.addWidget(self.back_btn)
        layout.addWidget(self.next_btn)


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setText(text)
        self.setToolTip(text)

    def setText(self, text: str):  # noqa: N802 - Qt method name
        self._full_text = text
        super().setText(text)
        self.setToolTip(text)

    def resizeEvent(self, event):  # noqa: N802 - Qt method name
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, Qt.TextElideMode.ElideMiddle, self.width()))
        super().resizeEvent(event)


def panel() -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    frame.setStyleSheet(f"""
        QFrame#panel {{
            background-color: {Colors.SURFACE};
            border: 1px solid {Colors.BORDER};
            border-radius: 10px;
        }}
    """)
    return frame
```

- [ ] **Step 3: Fix `components.py` bold font usage before running compile**

Replace the two `Weight.Bold` calls in `components.py` with direct `QFont.Weight.Bold` and import `QFont`:

```python
from PyQt6.QtGui import QFont, QFontMetrics
```

```python
self.title_label.setFont(font(20, QFont.Weight.Bold))
```

```python
self.badge.setFont(font(10, QFont.Weight.Bold))
```

- [ ] **Step 4: Compile the new files**

Run:

```bash
python3 -m py_compile downloader/ui/theme.py downloader/ui/components.py
```

Expected: command exits with code `0` and prints no output.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add downloader/ui/theme.py downloader/ui/components.py
git commit -m "feat: add shared ui theme components"
```

Expected: commit succeeds.

---

### Task 2: Rebuild Wizard Shell As Left Brand Sidebar

**Files:**
- Modify: `downloader/ui/wizard.py`
- Verify: `python3 -m py_compile downloader/ui/wizard.py`
- Commit: `feat: add branded wizard shell`

- [ ] **Step 1: Update `wizard.py` imports**

Replace the current imports from `PyQt6.QtWidgets` and add theme/component imports:

```python
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.components import SidebarStepItem
from downloader.ui.theme import Colors, font
```

- [ ] **Step 2: Change window size and root layout**

In `_setup_ui`, replace the size and top-level layout setup with:

```python
self.setWindowTitle("登临部署包下载工具V0.1")
self.setMinimumSize(860, 600)
self.resize(940, 640)

main_layout = QHBoxLayout(self)
main_layout.setContentsMargins(0, 0, 0, 0)
main_layout.setSpacing(0)

self._sidebar = self._create_sidebar()
main_layout.addWidget(self._sidebar)

self.stack = QStackedWidget()
self.stack.setStyleSheet(f"background-color: {Colors.PAGE_BG};")
main_layout.addWidget(self.stack, 1)
```

Delete the old `_step_bar`, horizontal separator line, and `main_layout.addWidget(self.stack, 1)` from the previous vertical layout.

- [ ] **Step 3: Replace `_create_step_bar` with `_create_sidebar`**

Delete `_create_step_bar`. Add:

```python
def _create_sidebar(self) -> QWidget:
    sidebar = QWidget()
    sidebar.setFixedWidth(236)
    sidebar.setStyleSheet(f"background-color: {Colors.SIDEBAR};")

    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(20, 24, 20, 20)
    layout.setSpacing(18)

    brand = QLabel("DengLin")
    brand.setFont(font(22, QFont.Weight.Bold))
    brand.setStyleSheet("color: white;")
    layout.addWidget(brand)

    app_name = QLabel("部署包下载工具")
    app_name.setFont(font(11))
    app_name.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
    layout.addWidget(app_name)

    version = QLabel("V0.1")
    version.setFont(font(9))
    version.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
    layout.addWidget(version)

    divider = QFrame()
    divider.setFrameShape(QFrame.Shape.HLine)
    divider.setStyleSheet("background-color: #334155; max-height: 1px;")
    layout.addWidget(divider)

    self._step_items: list[SidebarStepItem] = []
    for index, title in enumerate(["连接服务器", "发布配置", "选择内容", "下载任务"], start=1):
        item = SidebarStepItem(index, title)
        layout.addWidget(item)
        self._step_items.append(item)

    layout.addStretch(1)

    self._summary_title = QLabel("当前任务")
    self._summary_title.setFont(font(10, QFont.Weight.Bold))
    self._summary_title.setStyleSheet("color: white;")
    layout.addWidget(self._summary_title)

    self._summary_label = QLabel("等待连接服务器")
    self._summary_label.setWordWrap(True)
    self._summary_label.setFont(font(9))
    self._summary_label.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
    layout.addWidget(self._summary_label)

    return sidebar
```

- [ ] **Step 4: Replace `_update_steps`**

Replace `_update_steps` with:

```python
def _update_steps(self, current: int):
    for i, item in enumerate(self._step_items):
        if i < current:
            item.set_state("done")
        elif i == current:
            item.set_state("current")
        else:
            item.set_state("pending")
    self._update_sidebar_summary(current)

def _update_sidebar_summary(self, current: int):
    if current == 0:
        text = "等待连接服务器"
    elif current == 1:
        text = f"账号: {self._username or '-'}"
    elif current == 2:
        if self._release_type == "custom":
            text = f"定制发布\n{self._selected_version or '-'}"
        else:
            text = (
                f"标准发布\n"
                f"{self._selected_arch or '-'} | {self._selected_os or '-'}\n"
                f"{self._selected_version or '-'}"
            )
    else:
        text = "准备下载所选文件"
    self._summary_label.setText(text)
```

- [ ] **Step 5: Compile wizard**

Run:

```bash
python3 -m py_compile downloader/ui/wizard.py
```

Expected: exits `0`.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add downloader/ui/wizard.py
git commit -m "feat: add branded wizard shell"
```

Expected: commit succeeds.

---

### Task 3: Rebuild Connection Page

**Files:**
- Modify: `downloader/ui/welcome_page.py`
- Verify: `python3 -m py_compile downloader/ui/welcome_page.py`
- Commit: `feat: redesign connection page`

- [ ] **Step 1: Update imports**

Remove `QFrame` and `QHBoxLayout` if no longer used. Add:

```python
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.components import PageHeader
from downloader.ui.theme import Colors, button_style, input_style, font
```

- [ ] **Step 2: Replace `_setup_ui` content**

Replace the body of `_setup_ui` with:

```python
layout = QVBoxLayout(self)
layout.setContentsMargins(44, 38, 44, 34)
layout.setSpacing(24)

header = PageHeader(
    "连接服务器",
    f"SFTP 服务器: {SFTP_HOST}:{SFTP_PORT}",
)
layout.addWidget(header)

layout.addStretch(1)

form = QWidget()
form.setFixedWidth(400)
form_layout = QVBoxLayout(form)
form_layout.setContentsMargins(0, 0, 0, 0)
form_layout.setSpacing(10)

form_layout.addWidget(self._make_label("用户名"))
self.username_edit = QLineEdit()
self.username_edit.setMinimumHeight(40)
self.username_edit.setFont(font(11))
self.username_edit.setPlaceholderText("请输入用户名")
self.username_edit.setStyleSheet(input_style())
self.username_edit.textChanged.connect(self._validate_inputs)
form_layout.addWidget(self.username_edit)

form_layout.addSpacing(6)
form_layout.addWidget(self._make_label("密码"))
self.password_edit = QLineEdit()
self.password_edit.setMinimumHeight(40)
self.password_edit.setFont(font(11))
self.password_edit.setPlaceholderText("请输入密码")
self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
self.password_edit.setStyleSheet(input_style())
self.password_edit.textChanged.connect(self._validate_inputs)
form_layout.addWidget(self.password_edit)

self.remember_cb = QCheckBox("记住密码")
self.remember_cb.setFont(font(10))
self.remember_cb.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
form_layout.addWidget(self.remember_cb)

self.start_btn = QPushButton("连接并继续")
self.start_btn.setMinimumHeight(44)
self.start_btn.setFont(font(12))
self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self.start_btn.setEnabled(False)
self.start_btn.setStyleSheet(button_style("primary"))
self.start_btn.clicked.connect(self._on_start)
form_layout.addSpacing(10)
form_layout.addWidget(self.start_btn)

layout.addWidget(form, 0, Qt.AlignmentFlag.AlignHCenter)
layout.addStretch(2)
```

- [ ] **Step 3: Update `_make_label`**

Replace `_make_label` with:

```python
@staticmethod
def _make_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(font(10))
    label.setStyleSheet(f"color: {Colors.TEXT};")
    return label
```

- [ ] **Step 4: Compile welcome page**

Run:

```bash
python3 -m py_compile downloader/ui/welcome_page.py
```

Expected: exits `0`.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add downloader/ui/welcome_page.py
git commit -m "feat: redesign connection page"
```

Expected: commit succeeds.

---

### Task 4: Rebuild Release Config Page And Fix Version Default

**Files:**
- Modify: `downloader/ui/config_page.py`
- Verify: `python3 -m py_compile downloader/ui/config_page.py`
- Commit: `feat: redesign release config page`

- [ ] **Step 1: Replace local card classes usage**

Keep `ArchCardButton` and `OsCardButton` in place until the page compiles, but instantiate shared `SelectionCardButton` instead:

```python
from downloader.ui.components import FooterActions, PageHeader, SegmentedControl, SelectionCardButton
from downloader.ui.theme import Colors, button_style, input_style, font
```

In `_setup_ui`, create:

```python
layout = QVBoxLayout(self)
layout.setSpacing(20)
layout.setContentsMargins(44, 34, 44, 28)

self.header = PageHeader("发布配置", "选择发布类型、目标平台和版本来源")
layout.addWidget(self.header)
```

- [ ] **Step 2: Replace release buttons with `SegmentedControl`**

Replace the release button creation block with:

```python
self._release_container = QWidget()
release_outer = QVBoxLayout(self._release_container)
release_outer.setContentsMargins(0, 0, 0, 0)
release_outer.setSpacing(8)

release_title = QLabel("发布类型")
release_title.setFont(font(12, QFont.Weight.Bold))
release_title.setStyleSheet(f"color: {Colors.TEXT};")
release_outer.addWidget(release_title)

self.release_control = SegmentedControl([
    ("standard", "标准发布"),
    ("custom", "定制发布"),
])
self._release_btns = self.release_control.buttons
for key, btn in self._release_btns.items():
    btn.clicked.connect(lambda checked, k=key: self._on_release_type_changed(k))
release_outer.addWidget(self.release_control)
self._release_container.setVisible(False)
content_layout.addWidget(self._release_container)
```

After the scroll content setup, keep:

```python
self.release_control.set_checked("standard")
```

- [ ] **Step 3: Use `SelectionCardButton` for arch cards**

Replace arch card creation with:

```python
self.x86_btn = SelectionCardButton("x86_64", "Intel / AMD 64位")
self.x86_btn.setMinimumSize(210, 76)
self.arm64_btn = SelectionCardButton("arm64", "ARM 64位 (aarch64)")
self.arm64_btn.setMinimumSize(210, 76)
```

Keep the existing `QButtonGroup` logic.

- [ ] **Step 4: Use `SelectionCardButton` for OS cards**

Replace OS card creation with:

```python
for os_info in OS_OPTIONS:
    btn = SelectionCardButton(os_info["label"], os_info["desc"])
    btn.setMinimumSize(150, 64)
    self._os_group.addButton(btn)
    self._os_btns[os_info["key"]] = btn
    os_layout.addWidget(btn)
```

- [ ] **Step 5: Restyle combo and refresh button**

After creating `self.version_combo` and `self.refresh_btn`, set:

```python
self.version_combo.setMinimumHeight(38)
self.version_combo.setStyleSheet(input_style())
self.refresh_btn.setMinimumSize(74, 38)
self.refresh_btn.setStyleSheet(button_style("secondary"))
```

Do not keep fixed `60x32` size.

- [ ] **Step 6: Replace bottom buttons with `FooterActions`**

Replace the manual `btn_layout`, `back_btn`, and `next_btn` construction with:

```python
self.footer = FooterActions()
self.back_btn = self.footer.back_btn
self.next_btn = self.footer.next_btn
self.back_btn.clicked.connect(self.back_clicked.emit)
self.next_btn.clicked.connect(self._on_next)
layout.addWidget(self.footer)
```

- [ ] **Step 7: Fix default version selection and empty lists**

Replace `_on_versions_loaded` with:

```python
def _on_versions_loaded(self, versions: list[str]):
    self._versions = versions
    self.version_combo.clear()
    self.version_combo.addItems(versions)
    has_versions = bool(versions)
    self.version_combo.setEnabled(has_versions)
    self.next_btn.setEnabled(has_versions)
    if has_versions:
        self.version_combo.setCurrentIndex(0)
        self.version_status.setText(f"找到 {len(versions)} 个版本（最新: {versions[0]}）")
    else:
        self.version_status.setText("未找到可用版本")
    self.refresh_btn.setEnabled(True)
```

Replace `_on_custom_folders_loaded` with:

```python
def _on_custom_folders_loaded(self, folders: list[str]):
    self._versions = folders
    self.version_combo.clear()
    self.version_combo.addItems(folders)
    has_folders = bool(folders)
    self.version_combo.setEnabled(has_folders)
    self.next_btn.setEnabled(has_folders)
    if has_folders:
        self.version_combo.setCurrentIndex(0)
        self.version_status.setText(f"找到 {len(folders)} 个定制文件夹")
    else:
        self.version_status.setText("未找到定制文件夹")
    self.refresh_btn.setEnabled(True)
```

In `_fetch_versions` and `_fetch_custom_folders`, add:

```python
self.next_btn.setEnabled(False)
```

before starting the worker.

- [ ] **Step 8: Compile config page**

Run:

```bash
python3 -m py_compile downloader/ui/config_page.py
```

Expected: exits `0`.

- [ ] **Step 9: Commit Task 4**

Run:

```bash
git add downloader/ui/config_page.py
git commit -m "feat: redesign release config page"
```

Expected: commit succeeds.

---

### Task 5: Rebuild Content Selection Page

**Files:**
- Modify: `downloader/ui/mode_selection_page.py`
- Verify: `python3 -m py_compile downloader/ui/mode_selection_page.py`
- Commit: `feat: redesign content selection page`

- [ ] **Step 1: Add shared imports**

Add:

```python
from downloader.ui.components import ElidedLabel, FooterActions, PageHeader, SelectionCardButton
from downloader.ui.theme import Colors, button_style, font
```

- [ ] **Step 2: Replace page header**

At the start of `_setup_ui`, use:

```python
layout = QVBoxLayout(self)
layout.setSpacing(18)
layout.setContentsMargins(44, 34, 44, 28)

self.header = PageHeader("选择下载内容", "选择预设或手动勾选组件")
layout.addWidget(self.header)

self.info_label = QLabel("")
self.info_label.setFont(font(10))
self.info_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
layout.addWidget(self.info_label)
```

Remove the old `self.title` label.

- [ ] **Step 3: Convert preset buttons to shared selection cards**

In the preset loop, replace each `QPushButton` setup with:

```python
btn = SelectionCardButton(preset["label"])
btn.setMinimumSize(168, 54)
btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))
self._preset_group.addButton(btn)
self._preset_btns[key] = btn
self.preset_layout.addWidget(btn)
```

- [ ] **Step 4: Improve disabled component state**

Inside `_setup_standard_mode`, when a category is disabled for restricted OS, set tooltip:

```python
if cat_key in OS_DISABLED_CATEGORIES:
    restricted = is_restricted
    cb.setEnabled(not restricted)
    cb.setToolTip("当前操作系统不支持该组件" if restricted else "")
    if restricted:
        cb.setChecked(False)
else:
    cb.setEnabled(True)
    cb.setToolTip("")
```

- [ ] **Step 5: Use elided labels for custom file checkboxes**

In `_on_custom_files_loaded`, after creating each checkbox, set tooltip and minimum height:

```python
cb = QCheckBox(fname)
cb.setFont(font(10))
cb.setCursor(Qt.CursorShape.PointingHandCursor)
cb.setToolTip(fname)
cb.setMinimumHeight(26)
cb.setStyleSheet("QCheckBox { spacing: 8px; }")
```

Do not replace `QCheckBox` with `ElidedLabel` because it must remain selectable; tooltip is the stable improvement for dynamic checkboxes.

- [ ] **Step 6: Replace bottom buttons with `FooterActions`**

Replace the manual bottom button setup with:

```python
self.footer = FooterActions()
self.back_btn = self.footer.back_btn
self.next_btn = self.footer.next_btn
self.back_btn.clicked.connect(self.back_clicked.emit)
self.next_btn.clicked.connect(self._on_next)
layout.addWidget(self.footer)
```

- [ ] **Step 7: Update header on enter**

At the start of `on_enter`, after state assignment:

```python
if release_type == "custom":
    self.header.set_text("选择下载内容", "从定制发布文件夹中选择需要下载的文件")
else:
    self.header.set_text("选择下载内容", "选择预设或手动勾选标准发布组件")
```

- [ ] **Step 8: Compile mode selection page**

Run:

```bash
python3 -m py_compile downloader/ui/mode_selection_page.py
```

Expected: exits `0`.

- [ ] **Step 9: Commit Task 5**

Run:

```bash
git add downloader/ui/mode_selection_page.py
git commit -m "feat: redesign content selection page"
```

Expected: commit succeeds.

---

### Task 6: Rebuild Download Task Page And Fix Progress Issues

**Files:**
- Modify: `downloader/ui/download_page.py`
- Verify: `python3 -m py_compile downloader/ui/download_page.py`
- Commit: `feat: redesign download task page`

- [ ] **Step 1: Add shared imports**

Add:

```python
from downloader.ui.components import ElidedLabel, PageHeader, panel
from downloader.ui.theme import Colors, button_style, input_style, font
```

- [ ] **Step 2: Replace title and root layout**

At the start of `_setup_ui`, use:

```python
layout = QVBoxLayout(self)
layout.setSpacing(16)
layout.setContentsMargins(44, 34, 44, 28)

self.header = PageHeader("下载任务", "确认文件列表、保存目录和下载进度")
layout.addWidget(self.header)
```

Remove the old `title = QLabel("下载文件")` block.

- [ ] **Step 3: Keep file list but improve label and height**

Use:

```python
self.file_list_label = QLabel("匹配到的文件")
self.file_list_label.setFont(font(11, QFont.Weight.Bold))
self.file_list_label.setStyleSheet(f"color: {Colors.TEXT};")
layout.addWidget(self.file_list_label)

self.file_list_area = QScrollArea()
self.file_list_area.setWidgetResizable(True)
self.file_list_area.setMaximumHeight(150)
self.file_list_area.setStyleSheet(f"""
    QScrollArea {{
        background-color: {Colors.SURFACE};
        border: 1px solid {Colors.BORDER};
        border-radius: 10px;
    }}
""")
```

- [ ] **Step 4: Restyle directory row**

After `self.dir_edit` and `self.browse_btn` are created, set:

```python
self.dir_edit.setMinimumHeight(38)
self.dir_edit.setStyleSheet(input_style())
self.browse_btn.setMinimumSize(74, 38)
self.browse_btn.setStyleSheet(button_style("secondary"))
```

- [ ] **Step 5: Split current filename from file progress**

Replace the current file progress row with:

```python
self.current_file_label = ElidedLabel("当前文件: -")
self.current_file_label.setFont(font(10))
self.current_file_label.setStyleSheet(f"color: {Colors.TEXT};")
layout.addWidget(self.current_file_label)

file_layout = QHBoxLayout()
self.file_progress = QProgressBar()
self.file_progress.setTextVisible(True)
file_layout.addWidget(self.file_progress, 1)

self.speed_label = QLabel("")
self.speed_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
self.speed_label.setFixedWidth(120)
file_layout.addWidget(self.speed_label)
layout.addLayout(file_layout)
```

- [ ] **Step 6: Restyle log box**

Set:

```python
self.log_box.setMaximumHeight(160)
self.log_box.setStyleSheet(f"""
    QPlainTextEdit {{
        background-color: {Colors.LOG_BG};
        color: {Colors.LOG_TEXT};
        border: none;
        border-radius: 10px;
        padding: 8px;
    }}
""")
```

- [ ] **Step 7: Restyle bottom buttons**

Set button styles after creation:

```python
self.back_btn.setMinimumSize(120, 40)
self.back_btn.setStyleSheet(button_style("secondary"))
self.download_btn.setMinimumSize(140, 40)
self.download_btn.setStyleSheet(button_style("primary"))
self.open_folder_btn.setMinimumSize(120, 40)
self.open_folder_btn.setStyleSheet(button_style("success"))
```

Remove fixed sizes that make translated text brittle.

- [ ] **Step 8: Use `ElidedLabel` for file list rows**

In `_on_files_loaded`, replace:

```python
item = QLabel(f"  [{label}] {os.path.basename(f)}")
item.setFont(QFont("Microsoft YaHei", 10))
self.file_list_layout.addWidget(item)
```

with:

```python
item = ElidedLabel(f"[{label}] {os.path.basename(f)}")
item.setFont(font(10))
item.setStyleSheet(f"color: {Colors.TEXT};")
self.file_list_layout.addWidget(item)
```

In `_show_file_list`, replace `QLabel` rows with:

```python
item = ElidedLabel(os.path.basename(f))
item.setFont(font(10))
item.setStyleSheet(f"color: {Colors.TEXT};")
self.file_list_layout.addWidget(item)
```

- [ ] **Step 9: Fix current file progress state**

Replace `_on_file_progress` with:

```python
def _on_file_progress(self, filename: str, transferred: int, total: int):
    self.current_file_label.setText(f"当前文件: {filename}")
    if total > 0:
        self.file_progress.setMaximum(total)
        self.file_progress.setValue(transferred)
        pct = transferred / total * 100
        self.file_progress.setFormat(f"{pct:.1f}%")

        elapsed = time.time() - self._current_file_start_time
        if elapsed > 0.5 and transferred > 0:
            speed = (transferred - self._current_file_transferred) / elapsed
            self._current_file_start_time = time.time()
            self._current_file_transferred = transferred
            if speed > 0:
                self.speed_label.setText(self._format_size(speed) + "/s")
```

- [ ] **Step 10: Remove duplicate `_on_file_completed`**

Keep only one `_on_file_completed`:

```python
def _on_file_completed(self, filename: str):
    self._log(f"✓ {filename} 下载完成")
    self._current_file_start_time = time.time()
    self._current_file_transferred = 0
```

Delete the second duplicate method that only logs.

- [ ] **Step 11: Compile download page**

Run:

```bash
python3 -m py_compile downloader/ui/download_page.py
```

Expected: exits `0`.

- [ ] **Step 12: Commit Task 6**

Run:

```bash
git add downloader/ui/download_page.py
git commit -m "feat: redesign download task page"
```

Expected: commit succeeds.

---

### Task 7: Reduce Global Stylesheet

**Files:**
- Modify: `downloader/main.py`
- Verify: `python3 -m py_compile downloader/main.py`
- Commit: `refactor: simplify global ui stylesheet`

- [ ] **Step 1: Replace `app.setStyleSheet` content**

Use:

```python
app.setStyleSheet("""
    QWidget {
        font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    }
    QProgressBar {
        border: 1px solid #D8DEE8;
        border-radius: 8px;
        text-align: center;
        background-color: #F8FAFC;
        min-height: 22px;
    }
    QProgressBar::chunk {
        background-color: #2563EB;
        border-radius: 7px;
    }
    QCheckBox {
        spacing: 8px;
        color: #111827;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
""")
```

- [ ] **Step 2: Compile main**

Run:

```bash
python3 -m py_compile downloader/main.py
```

Expected: exits `0`.

- [ ] **Step 3: Commit Task 7**

Run:

```bash
git add downloader/main.py
git commit -m "refactor: simplify global ui stylesheet"
```

Expected: commit succeeds.

---

### Task 8: Add Offscreen Screenshot Verification Helper

**Files:**
- Create: `docs/superpowers/plans/scripts/render_branded_ui.py`
- Verify: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 docs/superpowers/plans/scripts/render_branded_ui.py`
- Commit: `test: add branded ui render helper`

- [ ] **Step 1: Create script directory**

Run:

```bash
mkdir -p docs/superpowers/plans/scripts
```

Expected: directory exists.

- [ ] **Step 2: Add render helper**

Use `apply_patch` to add:

```python
"""Render representative UI states for visual QA."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from downloader.ui.wizard import WizardWindow


OUT_DIR = Path("/private/tmp/byjdldown_branded_ui")


def render():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    QCoreApplication.setOrganizationName("DengLin")
    QCoreApplication.setApplicationName("vLLMDownloader")

    window = WizardWindow()
    window.resize(940, 640)
    window.show()
    app.processEvents()
    window.grab().save(str(OUT_DIR / "01_connection.png"))

    window.stack.setCurrentIndex(1)
    window._update_steps(1)
    config = window.config_page
    config._release_container.setVisible(True)
    config._release_btns["standard"].setChecked(True)
    config.x86_btn.setChecked(True)
    if "linux" in config._os_btns:
        config._os_btns["linux"].setChecked(True)
    config.version_combo.clear()
    config.version_combo.addItems([
        "V2-General_release-20260430",
        "V2-General_release-20260420",
    ])
    config.version_combo.setCurrentIndex(0)
    config.version_combo.setEnabled(True)
    config.version_status.setText("找到 2 个版本（最新: V2-General_release-20260430）")
    config.next_btn.setEnabled(True)
    app.processEvents()
    window.grab().save(str(OUT_DIR / "02_config_standard.png"))

    window.stack.setCurrentIndex(2)
    window._update_steps(2)
    mode = window.mode_page
    mode.on_enter("x86", "V2-General_release-20260430", "linux", "user", "pass", "standard")
    first_preset = next(iter(mode._preset_btns))
    mode._preset_btns[first_preset].setChecked(True)
    mode._on_preset_clicked(first_preset)
    app.processEvents()
    window.grab().save(str(OUT_DIR / "03_content_selection.png"))

    window.stack.setCurrentIndex(3)
    window._update_steps(3)
    download = window.download_page
    download._category_labels = {"driver": "驱动包", "container": "容器包", "sdk": "SDK"}
    download._reset_state()
    download._on_files_loaded({
        "driver": ["Base_driver/dlinfer-driver-manylinux-super-long-x86_64-release-package.tar.gz"],
        "container": ["Docker/container-x86-linux.tar.gz"],
        "sdk": ["SDK/dl-sdk-linux-x86_64.tar.gz"],
    }, [])
    download.dir_edit.setText("/Users/baiyunjun/Downloads")
    download.overall_progress.setMaximum(3)
    download.overall_progress.setValue(1)
    download.overall_progress.setFormat("1/3")
    download._on_file_progress(
        "dlinfer-driver-manylinux-super-long-x86_64-release-package.tar.gz",
        42,
        100,
    )
    download.speed_label.setText("12.5 MB/s")
    download._log("正在下载示例文件...")
    app.processEvents()
    window.grab().save(str(OUT_DIR / "04_download_task.png"))

    print(OUT_DIR)


if __name__ == "__main__":
    render()
```

- [ ] **Step 3: Run render helper**

Run:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 docs/superpowers/plans/scripts/render_branded_ui.py
```

Expected: prints `/private/tmp/byjdldown_branded_ui` and creates four PNG files:

```text
/private/tmp/byjdldown_branded_ui/01_connection.png
/private/tmp/byjdldown_branded_ui/02_config_standard.png
/private/tmp/byjdldown_branded_ui/03_content_selection.png
/private/tmp/byjdldown_branded_ui/04_download_task.png
```

- [ ] **Step 4: Inspect generated screenshots**

Open or view each PNG and verify:

```text
01_connection.png: left sidebar visible, connection form centered, button enabled only after credentials.
02_config_standard.png: standard release selected, x86 and Linux selected, version combo displays V2-General_release-20260430.
03_content_selection.png: preset cards and component checkboxes fit without overlapping the footer.
04_download_task.png: long current filename is on its own line, progress bar remains wide, log box is readable.
```

- [ ] **Step 5: Commit Task 8**

Run:

```bash
git add docs/superpowers/plans/scripts/render_branded_ui.py
git commit -m "test: add branded ui render helper"
```

Expected: commit succeeds.

---

### Task 9: Final Verification And Cleanup

**Files:**
- Verify all modified Python files.
- Review git diff.
- Commit only if cleanup changes are made.

- [ ] **Step 1: Run full syntax check**

Run:

```bash
python3 -m py_compile \
  downloader/main.py \
  downloader/ui/theme.py \
  downloader/ui/components.py \
  downloader/ui/wizard.py \
  downloader/ui/welcome_page.py \
  downloader/ui/config_page.py \
  downloader/ui/mode_selection_page.py \
  downloader/ui/download_page.py
```

Expected: exits `0` with no output.

- [ ] **Step 2: Run screenshot verification again**

Run:

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 docs/superpowers/plans/scripts/render_branded_ui.py
```

Expected: exits `0`, prints `/private/tmp/byjdldown_branded_ui`.

- [ ] **Step 3: Check for unresolved duplicate methods**

Run:

```bash
rg -n "def _on_file_completed|def _on_overall_progress" downloader/ui/download_page.py
```

Expected output contains exactly one `_on_file_completed` and one `_on_overall_progress`.

- [ ] **Step 4: Check for unresolved marker text in UI output**

Run:

```bash
rg -n "T[B]D|TO[D]O|pass$" downloader/ui docs/superpowers/plans/scripts/render_branded_ui.py
```

Expected: no matches, unless `pass` appears as a normal password variable in existing code. If only existing password names match, no code change is needed.

- [ ] **Step 5: Review working tree**

Run:

```bash
git status --short
git diff --stat
```

Expected: no unstaged changes after task commits. If cleanup edits are needed, stage and commit them:

```bash
git add downloader/main.py downloader/ui docs/superpowers/plans/scripts/render_branded_ui.py
git commit -m "chore: finalize branded ui polish"
```

---

## Self-Review Notes

- Spec coverage: the tasks cover theme extraction, left sidebar shell, all four page redesigns, version default selection, long filename layout, duplicate progress method fix, global stylesheet cleanup, and offscreen verification.
- Marker scan: this plan uses concrete file paths, commands, code snippets, and expected outputs. It does not rely on unspecified future decisions.
- Type consistency: shared component names match the spec: `PageHeader`, `SidebarStepItem`, `SelectionCardButton`, `SegmentedControl`, `FooterActions`, `ElidedLabel`.
