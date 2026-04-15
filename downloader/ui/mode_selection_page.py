"""向导页面 3：下载模式选择页（预设 + 组件勾选）"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from downloader.config import CUSTOM_CATEGORIES, OS_DISABLED_CATEGORIES, PRESETS
from downloader.workers import FetchCustomFilesWorker


class ModeSelectionPage(QWidget):
    """下载模式选择页：预设按钮 + 组件勾选（标准发布）或动态文件勾选（定制发布）"""

    next_clicked = pyqtSignal(dict)  # {"categories": [...], ...} or {"files": [...], ...}
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._arch = ""
        self._version = ""
        self._os = ""
        self._username = ""
        self._password = ""
        self._release_type = "standard"
        self._preset_btns: dict[str, QPushButton] = {}
        self._category_cbs: dict[str, QCheckBox] = {}
        self._custom_file_cbs: list[QCheckBox] = []
        self._sdk_linked: set[str] = {"cuda11"}
        self._auto_updating = False
        self._fetch_custom_worker: FetchCustomFilesWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(60, 30, 60, 30)

        # 标题
        self.title = QLabel("选择下载内容")
        self.title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(self.title)

        # 当前选择信息
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Microsoft YaHei", 10))
        self.info_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.info_label)

        # === 预设按钮区域（标准发布） ===
        self._preset_container = QWidget()
        preset_outer = QVBoxLayout(self._preset_container)
        preset_outer.setContentsMargins(0, 0, 0, 0)
        preset_outer.setSpacing(8)

        self.preset_title = QLabel("快速选择")
        self.preset_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        preset_outer.addWidget(self.preset_title)

        self.preset_layout = QHBoxLayout()
        self.preset_layout.setSpacing(16)

        self._preset_group = QButtonGroup(self)
        for key, preset in PRESETS.items():
            btn = QPushButton(preset["label"])
            btn.setFixedSize(160, 50)
            btn.setFont(QFont("Microsoft YaHei", 12))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F8F8F8;
                    border: 2px solid #DDDDDD;
                    border-radius: 8px;
                    color: #333333;
                }
                QPushButton:hover {
                    border-color: #AAAAAA;
                }
                QPushButton:checked {
                    background-color: #E8F0FE;
                    border: 2px solid #4A90D9;
                    color: #4A90D9;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))
            self._preset_group.addButton(btn)
            self._preset_btns[key] = btn
            self.preset_layout.addWidget(btn)

        self.preset_layout.addStretch(1)
        preset_outer.addLayout(self.preset_layout)

        layout.addWidget(self._preset_container)

        layout.addSpacing(8)

        # === 标准发布：固定下载组件 checkbox ===
        self._category_container = QWidget()
        cat_outer = QVBoxLayout(self._category_container)
        cat_outer.setContentsMargins(0, 0, 0, 0)
        cat_outer.setSpacing(8)

        cat_title = QLabel("下载组件")
        cat_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        cat_outer.addWidget(cat_title)

        cat_container = QWidget()
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setSpacing(20)
        cat_layout.setContentsMargins(0, 0, 0, 0)

        col_left = QVBoxLayout()
        col_left.setSpacing(8)
        col_right = QVBoxLayout()
        col_right.setSpacing(8)

        cat_keys = list(CUSTOM_CATEGORIES.keys())
        mid = (len(cat_keys) + 1) // 2
        for i, cat_key in enumerate(cat_keys):
            cat_config = CUSTOM_CATEGORIES[cat_key]
            cb = QCheckBox(cat_config["label"])
            cb.setFont(QFont("Microsoft YaHei", 11))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("QCheckBox { spacing: 6px; }")
            self._category_cbs[cat_key] = cb
            if cat_key == "sdk":
                cb.toggled.connect(self._on_sdk_toggled)
            if i < mid:
                col_left.addWidget(cb)
            else:
                col_right.addWidget(cb)

        col_left.addStretch(1)
        col_right.addStretch(1)
        cat_layout.addLayout(col_left)
        cat_layout.addLayout(col_right)
        cat_outer.addWidget(cat_container)

        layout.addWidget(self._category_container)

        # === 定制发布：动态文件 checkbox 区域 ===
        self._custom_container = QWidget()
        custom_outer = QVBoxLayout(self._custom_container)
        custom_outer.setContentsMargins(0, 0, 0, 0)
        custom_outer.setSpacing(8)

        self._custom_title = QLabel("选择要下载的文件")
        self._custom_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        custom_outer.addWidget(self._custom_title)

        self._custom_scroll = QScrollArea()
        self._custom_scroll.setWidgetResizable(True)
        self._custom_scroll.setMaximumHeight(250)
        self._custom_content = QWidget()
        self._custom_content_layout = QVBoxLayout(self._custom_content)
        self._custom_content_layout.setSpacing(6)
        self._custom_content_layout.setContentsMargins(8, 8, 8, 8)
        self._custom_scroll.setWidget(self._custom_content)
        custom_outer.addWidget(self._custom_scroll)

        self._custom_status = QLabel("")
        self._custom_status.setStyleSheet("color: #888888; font-size: 12px;")
        custom_outer.addWidget(self._custom_status)

        self._custom_container.setVisible(False)
        layout.addWidget(self._custom_container)

        layout.addStretch(1)

        # === 底部按钮 ===
        btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setFixedSize(120, 40)
        self.back_btn.setFont(QFont("Microsoft YaHei", 11))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #E0E0E0; }
        """)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.next_btn = QPushButton("下一步")
        self.next_btn.setFixedSize(120, 40)
        self.next_btn.setFont(QFont("Microsoft YaHei", 11))
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3A7BC8; }
            QPushButton:pressed { background-color: #2E6AB5; }
            QPushButton:disabled { background-color: #AAAAAA; }
        """)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def on_enter(self, arch: str, version: str, os_name: str,
                 username: str, password: str, release_type: str = "standard"):
        """进入页面时设置上下文信息"""
        self._arch = arch
        self._version = version
        self._os = os_name
        self._username = username
        self._password = password
        self._release_type = release_type

        # 更新信息标签
        if release_type == "custom":
            self.info_label.setText(f"当前: 定制发布 | {version}")
        else:
            arch_display = "x86_64" if arch == "x86" else "ARM64"
            os_display = os_name.capitalize()
            self.info_label.setText(f"当前: {arch_display} | {os_display} | {version}")

        if release_type == "custom":
            self._setup_custom_mode()
        else:
            self._setup_standard_mode(os_name)

    def _setup_standard_mode(self, os_name: str):
        """标准发布模式：显示预设 + 固定checkbox"""
        self._preset_container.setVisible(True)
        self._category_container.setVisible(True)
        self._custom_container.setVisible(False)

        is_restricted = os_name in ("windows", "centos")

        vllm_btn = self._preset_btns.get("vllm")
        if vllm_btn:
            vllm_btn.setVisible(not is_restricted)

        for cat_key, cb in self._category_cbs.items():
            if cat_key in OS_DISABLED_CATEGORIES:
                cb.setEnabled(not is_restricted)
                if is_restricted:
                    cb.setChecked(False)
            else:
                cb.setEnabled(True)

        self._preset_group.setExclusive(False)
        for btn in self._preset_btns.values():
            btn.setChecked(False)
        self._preset_group.setExclusive(True)

    def _setup_custom_mode(self):
        """定制发布模式：隐藏预设，动态获取文件列表生成checkbox"""
        self._preset_container.setVisible(False)
        self._category_container.setVisible(False)
        self._custom_container.setVisible(True)

        # 清除旧的动态 checkbox
        self._clear_custom_checkboxes()
        self._custom_status.setText("正在获取文件列表...")

        # 后台获取定制文件夹中的文件
        self._fetch_custom_worker = FetchCustomFilesWorker(
            self._username, self._password, self._version
        )
        self._fetch_custom_worker.success.connect(self._on_custom_files_loaded)
        self._fetch_custom_worker.error.connect(self._on_custom_files_error)
        self._fetch_custom_worker.start()

    def _clear_custom_checkboxes(self):
        """清除动态生成的文件 checkbox"""
        for cb in self._custom_file_cbs:
            self._custom_content_layout.removeWidget(cb)
            cb.deleteLater()
        self._custom_file_cbs.clear()

    def _on_custom_files_loaded(self, files: list[str]):
        """定制文件夹文件列表获取完成，生成 checkbox"""
        self._clear_custom_checkboxes()
        for fname in files:
            cb = QCheckBox(fname)
            cb.setFont(QFont("Microsoft YaHei", 10))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("QCheckBox { spacing: 6px; }")
            self._custom_content_layout.addWidget(cb)
            self._custom_file_cbs.append(cb)

        self._custom_content_layout.addStretch(1)
        self._custom_status.setText(f"共 {len(files)} 个文件")

    def _on_custom_files_error(self, msg: str):
        self._custom_status.setText(f"获取失败: {msg}")
        QMessageBox.warning(self, "获取文件列表失败", msg)

    def _on_preset_clicked(self, preset_key: str):
        """预设按钮被点击，自动勾选对应组件"""
        categories = PRESETS[preset_key]["categories"]
        self._auto_updating = True
        for cat_key, cb in self._category_cbs.items():
            cb.setChecked(cat_key in categories and cb.isEnabled())
        self._auto_updating = False

    def _on_sdk_toggled(self, checked: bool):
        """SDK 被勾选/取消时，自动勾选/取消 cuda11"""
        if self._auto_updating:
            return
        self._auto_updating = True
        for linked_key in self._sdk_linked:
            cb = self._category_cbs.get(linked_key)
            if cb and cb.isEnabled():
                cb.setChecked(checked)
        self._auto_updating = False

    def _on_next(self):
        """点击下一步：收集选中的项目，发射信号"""
        if self._release_type == "custom":
            selected_files = [
                cb.text() for cb in self._custom_file_cbs if cb.isChecked()
            ]
            if not selected_files:
                QMessageBox.warning(self, "请选择文件", "请至少勾选一个文件")
                return
            category_labels = {f: f for f in selected_files}
            self.next_clicked.emit({
                "files": selected_files,
                "category_labels": category_labels,
                "release_type": "custom",
            })
        else:
            selected = [key for key, cb in self._category_cbs.items() if cb.isChecked()]
            if not selected:
                QMessageBox.warning(self, "请选择组件", "请至少勾选一个下载组件")
                return
            category_labels = {
                key: CUSTOM_CATEGORIES[key]["label"] for key in selected
            }
            self.next_clicked.emit({
                "categories": selected,
                "category_labels": category_labels,
                "release_type": "standard",
            })
