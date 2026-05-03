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
from downloader.ui.components import FooterActions, PageHeader, SelectionCardButton
from downloader.ui.theme import Colors, font
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
        self._custom_files_request_id = 0
        self._custom_file_workers: list[FetchCustomFilesWorker] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(44, 34, 44, 28)

        self.header = PageHeader("选择下载内容", "选择预设或手动勾选组件")
        layout.addWidget(self.header)

        # 当前选择信息
        self.info_label = QLabel("")
        self.info_label.setFont(font(10))
        self.info_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.info_label)

        # === 预设按钮区域（标准发布） ===
        self._preset_container = QWidget()
        preset_outer = QVBoxLayout(self._preset_container)
        preset_outer.setContentsMargins(0, 0, 0, 0)
        preset_outer.setSpacing(8)

        self.preset_title = QLabel("快速选择")
        self.preset_title.setFont(font(12, QFont.Weight.Bold))
        preset_outer.addWidget(self.preset_title)

        self.preset_layout = QHBoxLayout()
        self.preset_layout.setSpacing(16)

        self._preset_group = QButtonGroup(self)
        self._preset_group.setExclusive(True)
        for key, preset in PRESETS.items():
            btn = SelectionCardButton(preset["label"])
            btn.setMinimumWidth(160)
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
        cat_title.setFont(font(12, QFont.Weight.Bold))
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
            cb.setFont(font(11))
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
        self._custom_title.setFont(font(12, QFont.Weight.Bold))
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
        self._custom_status.setFont(font(10))
        self._custom_status.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        custom_outer.addWidget(self._custom_status)

        self._custom_container.setVisible(False)
        layout.addWidget(self._custom_container)

        layout.addStretch(1)

        # === 底部按钮 ===
        self.footer = FooterActions()
        self.back_btn = self.footer.back_btn
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.next_btn = self.footer.next_btn
        self.next_btn.clicked.connect(self._on_next)
        layout.addWidget(self.footer)

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
            self.header.set_text("选择下载内容", "从定制发布文件夹中选择需要下载的文件")
            self.info_label.setText(f"当前: 定制发布 | {version}")
        else:
            self.header.set_text("选择下载内容", "选择预设或手动勾选标准发布组件")
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
                    cb.setToolTip("当前操作系统不支持该组件")
                else:
                    cb.setToolTip("")
            else:
                cb.setEnabled(True)
                cb.setToolTip("")

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
        self._custom_files_request_id += 1
        request_id = self._custom_files_request_id

        # 后台获取定制文件夹中的文件
        worker = FetchCustomFilesWorker(
            self._username, self._password, self._version
        )
        self._fetch_custom_worker = worker
        self._custom_file_workers.append(worker)
        worker.success.connect(
            lambda files, rid=request_id: self._handle_custom_files_loaded(rid, files)
        )
        worker.error.connect(
            lambda msg, rid=request_id: self._handle_custom_files_error(rid, msg)
        )
        worker.finished.connect(lambda w=worker: self._remove_custom_file_worker(w))
        worker.start()

    def _remove_custom_file_worker(self, worker: FetchCustomFilesWorker):
        """Release a completed custom file worker without touching active workers."""
        if worker in self._custom_file_workers:
            self._custom_file_workers.remove(worker)
        if self._fetch_custom_worker is worker:
            self._fetch_custom_worker = (
                self._custom_file_workers[-1] if self._custom_file_workers else None
            )

    def _is_current_custom_request(self, request_id: int) -> bool:
        return (
            request_id == self._custom_files_request_id
            and self._release_type == "custom"
        )

    def _handle_custom_files_loaded(self, request_id: int, files: list[str]):
        if self._is_current_custom_request(request_id):
            self._on_custom_files_loaded(files)

    def _handle_custom_files_error(self, request_id: int, msg: str):
        if self._is_current_custom_request(request_id):
            self._on_custom_files_error(msg)

    def _clear_custom_checkboxes(self):
        """清除动态生成的文件 checkbox 和尾部 spacer"""
        while self._custom_content_layout.count():
            item = self._custom_content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._custom_file_cbs.clear()

    def _on_custom_files_loaded(self, files: list[str]):
        """定制文件夹文件列表获取完成，生成 checkbox"""
        self._clear_custom_checkboxes()
        for fname in files:
            cb = QCheckBox(fname)
            cb.setFont(font(10))
            cb.setMinimumHeight(26)
            cb.setToolTip(fname)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet("QCheckBox { spacing: 8px; }")
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
