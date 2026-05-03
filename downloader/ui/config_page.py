"""向导页面 2：发布类型 + 架构选择 + 操作系统选择 + 版本选择"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from downloader.config import OS_OPTIONS
from downloader.ui.components import (
    FooterActions,
    PageHeader,
    SegmentedControl,
    SelectionCardButton,
)
from downloader.ui.theme import Colors, button_style, font, input_style
from downloader.workers import FetchCustomFoldersWorker, FetchVersionsWorker


class ConfigPage(QWidget):
    """配置页：发布类型 + 架构 + 操作系统 + 版本"""

    next_clicked = pyqtSignal(str, str, str, str)  # arch, version, os, release_type
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._versions: list[str] = []
        self._fetch_worker: FetchVersionsWorker | None = None
        self._fetch_custom_worker: FetchCustomFoldersWorker | None = None
        self._username = ""
        self._password = ""
        self._os_btns: dict[str, SelectionCardButton] = {}
        self._release_type = "standard"
        self._has_custom_folders: bool | None = None  # None=未检测, False=无, True=有
        self._detect_request_id = 0
        self._standard_request_id = 0
        self._custom_request_id = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(44, 34, 44, 28)

        layout.addWidget(PageHeader("发布配置", "选择发布类型、目标平台和版本来源"))

        # 使用 ScrollArea 包裹内容，防止窗口过小时遮挡
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # === 发布类型切换（初始隐藏，检测到有定制文件夹后才显示） ===
        self._release_container = QWidget()
        release_outer = QVBoxLayout(self._release_container)
        release_outer.setContentsMargins(0, 0, 0, 0)
        release_outer.setSpacing(8)

        release_title = QLabel("发布类型")
        release_title.setFont(font(12))
        release_title.setStyleSheet(f"color: {Colors.TEXT};")
        release_outer.addWidget(release_title)

        self._release_segment = SegmentedControl(
            [("standard", "标准发布"), ("custom", "定制发布")]
        )
        self._release_group = self._release_segment.group
        self._release_btns: dict[str, QPushButton] = self._release_segment.buttons
        for key, btn in self._release_btns.items():
            btn.clicked.connect(lambda checked, k=key: self._on_release_type_changed(k))
        release_outer.addWidget(self._release_segment)

        self._release_container.setVisible(False)  # 初始隐藏
        content_layout.addWidget(self._release_container)

        # === 架构选择区域（标准发布时显示） ===
        self._arch_container = QWidget()
        arch_outer = QVBoxLayout(self._arch_container)
        arch_outer.setContentsMargins(0, 0, 0, 0)
        arch_outer.setSpacing(8)

        arch_title = QLabel("请选择 CPU 架构")
        arch_title.setFont(font(12))
        arch_title.setStyleSheet(f"color: {Colors.TEXT};")
        arch_outer.addWidget(arch_title)

        arch_layout = QHBoxLayout()
        arch_layout.setSpacing(12)

        self.x86_btn = SelectionCardButton("x86_64", "Intel / AMD 64位")
        self.x86_btn.setMinimumWidth(200)

        self.arm64_btn = SelectionCardButton("arm64", "ARM 64位 (aarch64)")
        self.arm64_btn.setMinimumWidth(200)

        self._arch_group = QButtonGroup(self)
        self._arch_group.addButton(self.x86_btn)
        self._arch_group.addButton(self.arm64_btn)

        arch_layout.addStretch(1)
        arch_layout.addWidget(self.x86_btn)
        arch_layout.addWidget(self.arm64_btn)
        arch_layout.addStretch(1)
        arch_outer.addLayout(arch_layout)

        content_layout.addWidget(self._arch_container)

        # === 操作系统选择区域（标准发布时显示） ===
        self._os_container = QWidget()
        os_outer = QVBoxLayout(self._os_container)
        os_outer.setContentsMargins(0, 0, 0, 0)
        os_outer.setSpacing(8)

        os_title = QLabel("请选择操作系统")
        os_title.setFont(font(12))
        os_title.setStyleSheet(f"color: {Colors.TEXT};")
        os_outer.addWidget(os_title)

        os_layout = QHBoxLayout()
        os_layout.setSpacing(12)

        self._os_group = QButtonGroup(self)
        for os_info in OS_OPTIONS:
            btn = SelectionCardButton(os_info["label"], os_info["desc"])
            btn.setMinimumWidth(140)
            self._os_group.addButton(btn)
            self._os_btns[os_info["key"]] = btn
            os_layout.addWidget(btn)

        os_layout.addStretch(1)
        os_outer.addLayout(os_layout)

        content_layout.addWidget(self._os_container)

        # === 版本选择 ===
        ver_title = QLabel("选择 SDK 版本")
        ver_title.setFont(font(12))
        ver_title.setStyleSheet(f"color: {Colors.TEXT};")
        content_layout.addWidget(ver_title)

        ver_layout = QHBoxLayout()
        ver_layout.setSpacing(12)
        self.version_combo = QComboBox()
        self.version_combo.setFont(font(10))
        self.version_combo.setMinimumHeight(38)
        self.version_combo.setStyleSheet(input_style())
        self.version_combo.setEnabled(False)
        try:
            self.version_combo.setPlaceholderText("请选择 SDK 版本...")
        except AttributeError:
            pass
        ver_layout.addWidget(self.version_combo, 1)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMinimumSize(74, 38)
        self.refresh_btn.setFont(font(10))
        self.refresh_btn.setStyleSheet(button_style("secondary"))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._fetch_current_list)
        ver_layout.addWidget(self.refresh_btn)
        content_layout.addLayout(ver_layout)

        self.version_status = QLabel("")
        self.version_status.setFont(font(10))
        self.version_status.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        content_layout.addWidget(self.version_status)

        content_layout.addStretch(1)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # === 底部按钮 ===
        footer = FooterActions()
        self.back_btn = footer.back_btn
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.next_btn = footer.next_btn
        self.next_btn.clicked.connect(self._on_next)
        layout.addWidget(footer)

        # 默认选中标准发布
        self._release_segment.set_checked("standard")

    def _on_release_type_changed(self, release_type: str):
        """发布类型切换"""
        self._release_type = release_type
        is_standard = release_type == "standard"

        self._arch_container.setVisible(is_standard)
        self._os_container.setVisible(is_standard)

        self._versions = []
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self._fetch_current_list()

    def on_enter(self, username: str, password: str):
        """页面显示时检测定制文件夹并获取版本列表"""
        credentials_changed = (
            bool(self._username or self._password)
            and (username != self._username or password != self._password)
        )
        if credentials_changed:
            self._reset_release_state()

        self._username = username
        self._password = password

        if self._has_custom_folders is None:
            # 首次进入：先检测是否有定制文件夹
            self._check_custom_folders()
        elif not self._versions:
            self._fetch_current_list()

    def _reset_release_state(self):
        """Reset cached release choices when credentials change."""
        self._detect_request_id += 1
        self._standard_request_id += 1
        self._custom_request_id += 1
        self._has_custom_folders = None
        self._versions = []
        self._release_type = "standard"
        self._release_segment.set_checked("standard")
        self._release_container.setVisible(False)
        self._arch_container.setVisible(True)
        self._os_container.setVisible(True)
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.version_status.clear()

    def _check_custom_folders(self):
        """检测FTP是否有定制文件夹，决定是否显示发布类型切换"""
        self._detect_request_id += 1
        request_id = self._detect_request_id
        self.version_status.setText("正在检测服务器...")
        self.refresh_btn.setEnabled(False)

        self._fetch_custom_worker = FetchCustomFoldersWorker(self._username, self._password)
        self._fetch_custom_worker.success.connect(
            lambda folders, request_id=request_id: self._on_check_folders_result(
                folders, request_id
            )
        )
        self._fetch_custom_worker.error.connect(
            lambda msg, request_id=request_id: self._on_check_folders_error(
                msg, request_id
            )
        )
        self._fetch_custom_worker.start()

    def _on_check_folders_result(self, folders: list[str], request_id: int):
        """检测结果返回"""
        if request_id != self._detect_request_id:
            return

        has_custom = len(folders) > 0
        self._has_custom_folders = has_custom

        if has_custom:
            self._release_container.setVisible(True)

        # 继续获取标准版本列表
        self._fetch_versions()

    def _on_check_folders_error(self, msg: str, request_id: int):
        """检测失败，默认不显示切换按钮，直接获取标准版本"""
        if request_id != self._detect_request_id:
            return

        self._has_custom_folders = False
        self._release_container.setVisible(False)
        self._fetch_versions()

    def _fetch_current_list(self):
        """根据当前发布类型获取对应列表"""
        if self._release_type == "standard":
            self._fetch_versions()
        else:
            self._fetch_custom_folders()

    def _fetch_versions(self):
        """启动后台版本获取（标准发布）"""
        self._standard_request_id += 1
        request_id = self._standard_request_id
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_status.setText("正在获取版本列表...")
        self.refresh_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        self._fetch_worker = FetchVersionsWorker(self._username, self._password)
        self._fetch_worker.success.connect(
            lambda versions, request_id=request_id: self._on_versions_loaded(
                versions, request_id
            )
        )
        self._fetch_worker.error.connect(
            lambda msg, request_id=request_id: self._on_versions_error(
                msg, request_id
            )
        )
        self._fetch_worker.start()

    def _fetch_custom_folders(self):
        """启动后台定制文件夹获取（定制发布）"""
        self._custom_request_id += 1
        request_id = self._custom_request_id
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_status.setText("正在获取定制文件夹列表...")
        self.refresh_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        self._fetch_custom_worker = FetchCustomFoldersWorker(self._username, self._password)
        self._fetch_custom_worker.success.connect(
            lambda folders, request_id=request_id: self._on_custom_folders_loaded(
                folders, request_id
            )
        )
        self._fetch_custom_worker.error.connect(
            lambda msg, request_id=request_id: self._on_custom_folders_error(
                msg, request_id
            )
        )
        self._fetch_custom_worker.start()

    def _on_versions_loaded(self, versions: list[str], request_id: int):
        if self._release_type != "standard" or request_id != self._standard_request_id:
            return

        self._versions = versions
        self.version_combo.clear()
        has_versions = len(versions) > 0
        if has_versions:
            self.version_combo.addItems(versions)
            self.version_combo.setCurrentIndex(0)
            self.version_status.setText(f"找到 {len(versions)} 个版本（最新: {versions[0]}）")
        else:
            self.version_status.setText("未找到可用版本")
        self.version_combo.setEnabled(has_versions)
        self.next_btn.setEnabled(has_versions)
        self.refresh_btn.setEnabled(True)

    def _on_versions_error(self, msg: str, request_id: int):
        if self._release_type != "standard" or request_id != self._standard_request_id:
            return

        self.version_status.setText(f"获取失败: {msg}")
        self.refresh_btn.setEnabled(True)
        self.next_btn.setEnabled(False)
        QMessageBox.warning(self, "获取版本失败", msg)

    def _on_custom_folders_loaded(self, folders: list[str], request_id: int):
        if self._release_type != "custom" or request_id != self._custom_request_id:
            return

        self._versions = folders
        self.version_combo.clear()
        has_folders = len(folders) > 0
        if has_folders:
            self.version_combo.addItems(folders)
            self.version_combo.setCurrentIndex(0)
            self.version_status.setText(f"找到 {len(folders)} 个定制文件夹")
        else:
            self.version_status.setText("未找到定制文件夹")
        self.version_combo.setEnabled(has_folders)
        self.next_btn.setEnabled(has_folders)
        self.refresh_btn.setEnabled(True)

    def _on_custom_folders_error(self, msg: str, request_id: int):
        if self._release_type != "custom" or request_id != self._custom_request_id:
            return

        self.version_status.setText(f"获取失败: {msg}")
        self.refresh_btn.setEnabled(True)
        self.next_btn.setEnabled(False)
        QMessageBox.warning(self, "获取定制文件夹失败", msg)

    def _get_selected_os(self) -> str:
        for key, btn in self._os_btns.items():
            if btn.isChecked():
                return key
        return ""

    def _on_next(self):
        if self.version_combo.count() == 0:
            QMessageBox.warning(self, "无版本", "请等待列表加载完成")
            return

        version = self.version_combo.currentText()

        if self._release_type == "standard":
            if not self.x86_btn.isChecked() and not self.arm64_btn.isChecked():
                QMessageBox.warning(self, "请选择架构", "请先选择 CPU 架构")
                return
            selected_os = self._get_selected_os()
            if not selected_os:
                QMessageBox.warning(self, "请选择操作系统", "请先选择操作系统")
                return
            arch = "x86" if self.x86_btn.isChecked() else "arm64"
            self.next_clicked.emit(arch, version, selected_os, "standard")
        else:
            self.next_clicked.emit("", version, "", "custom")
