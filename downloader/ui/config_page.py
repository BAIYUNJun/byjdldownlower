"""向导页面 2：发布类型 + 架构选择 + 操作系统选择 + 版本选择"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from downloader.config import OS_OPTIONS
from downloader.workers import FetchCustomFoldersWorker, FetchVersionsWorker


class ArchCardButton(QPushButton):
    """架构选择卡片按钮"""

    def __init__(self, label: str, desc: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.desc = desc
        self.setFixedSize(200, 80)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._update_style)
        self._update_style()

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background-color: #E8F0FE;
                    border: 2px solid #4A90D9;
                    border-radius: 8px;
                    text-align: center;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #F8F8F8;
                    border: 2px solid #DDDDDD;
                    border-radius: 8px;
                    text-align: center;
                }
                QPushButton:hover {
                    border-color: #AAAAAA;
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style()


class OsCardButton(QPushButton):
    """操作系统选择卡片按钮"""

    def __init__(self, label: str, desc: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 60)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._update_style)
        self._update_style()

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background-color: #E8F0FE;
                    border: 2px solid #4A90D9;
                    border-radius: 8px;
                    text-align: center;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #F8F8F8;
                    border: 2px solid #DDDDDD;
                    border-radius: 8px;
                    text-align: center;
                }
                QPushButton:hover {
                    border-color: #AAAAAA;
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style()


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
        self._os_btns: dict[str, OsCardButton] = {}
        self._release_type = "standard"
        self._has_custom_folders: bool | None = None  # None=未检测, False=无, True=有
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(50, 20, 50, 20)

        # 使用 ScrollArea 包裹内容，防止窗口过小时遮挡
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # === 发布类型切换（初始隐藏，检测到有定制文件夹后才显示） ===
        self._release_container = QWidget()
        release_outer = QVBoxLayout(self._release_container)
        release_outer.setContentsMargins(0, 0, 0, 0)
        release_outer.setSpacing(6)

        release_title = QLabel("发布类型")
        release_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        release_outer.addWidget(release_title)

        release_layout = QHBoxLayout()
        release_layout.setSpacing(12)

        self._release_group = QButtonGroup(self)
        self._release_btns: dict[str, QPushButton] = {}
        for key, label in [("standard", "标准发布"), ("custom", "定制发布")]:
            btn = QPushButton(label)
            btn.setFixedSize(140, 40)
            btn.setFont(QFont("Microsoft YaHei", 11))
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
            btn.clicked.connect(lambda checked, k=key: self._on_release_type_changed(k))
            self._release_group.addButton(btn)
            self._release_btns[key] = btn
            release_layout.addWidget(btn)

        release_layout.addStretch(1)
        release_outer.addLayout(release_layout)

        self._release_container.setVisible(False)  # 初始隐藏
        content_layout.addWidget(self._release_container)

        # === 架构选择区域（标准发布时显示） ===
        self._arch_container = QWidget()
        arch_outer = QVBoxLayout(self._arch_container)
        arch_outer.setContentsMargins(0, 0, 0, 0)
        arch_outer.setSpacing(6)

        arch_title = QLabel("请选择 CPU 架构")
        arch_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        arch_outer.addWidget(arch_title)

        arch_layout = QHBoxLayout()
        arch_layout.setSpacing(16)

        self.x86_btn = ArchCardButton("x86_64", "Intel / AMD 64位")
        self.x86_btn.setText("x86_64\nIntel / AMD 64位")
        self.x86_btn.setFont(QFont("Microsoft YaHei", 10))

        self.arm64_btn = ArchCardButton("arm64", "ARM 64位")
        self.arm64_btn.setText("arm64\nARM 64位 (aarch64)")
        self.arm64_btn.setFont(QFont("Microsoft YaHei", 10))

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
        os_outer.setSpacing(6)

        os_title = QLabel("请选择操作系统")
        os_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        os_outer.addWidget(os_title)

        os_layout = QHBoxLayout()
        os_layout.setSpacing(12)

        self._os_group = QButtonGroup(self)
        for os_info in OS_OPTIONS:
            btn = OsCardButton(os_info["label"], os_info["desc"])
            btn.setText(f"{os_info['label']}\n{os_info['desc']}")
            btn.setFont(QFont("Microsoft YaHei", 10))
            self._os_group.addButton(btn)
            self._os_btns[os_info["key"]] = btn
            os_layout.addWidget(btn)

        os_layout.addStretch(1)
        os_outer.addLayout(os_layout)

        content_layout.addWidget(self._os_container)

        # === 版本选择 ===
        ver_title = QLabel("选择 SDK 版本")
        ver_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        content_layout.addWidget(ver_title)

        ver_layout = QHBoxLayout()
        self.version_combo = QComboBox()
        self.version_combo.setFont(QFont("Microsoft YaHei", 11))
        self.version_combo.setMinimumHeight(32)
        self.version_combo.setEnabled(False)
        try:
            self.version_combo.setPlaceholderText("请选择 SDK 版本...")
        except AttributeError:
            pass
        ver_layout.addWidget(self.version_combo, 1)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(60, 32)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._fetch_current_list)
        ver_layout.addWidget(self.refresh_btn)
        content_layout.addLayout(ver_layout)

        self.version_status = QLabel("")
        self.version_status.setStyleSheet("color: #888888; font-size: 11px;")
        content_layout.addWidget(self.version_status)

        content_layout.addStretch(1)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # === 底部按钮 ===
        btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setFixedSize(120, 36)
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
        self.next_btn.setFixedSize(120, 36)
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
        """)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

        # 默认选中标准发布
        self._release_btns["standard"].setChecked(True)

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
        self._username = username
        self._password = password

        if self._has_custom_folders is None:
            # 首次进入：先检测是否有定制文件夹
            self._check_custom_folders()
        elif not self._versions:
            self._fetch_current_list()

    def _check_custom_folders(self):
        """检测FTP是否有定制文件夹，决定是否显示发布类型切换"""
        self.version_status.setText("正在检测服务器...")
        self.refresh_btn.setEnabled(False)

        self._fetch_custom_worker = FetchCustomFoldersWorker(self._username, self._password)
        self._fetch_custom_worker.success.connect(self._on_check_folders_result)
        self._fetch_custom_worker.error.connect(self._on_check_folders_error)
        self._fetch_custom_worker.start()

    def _on_check_folders_result(self, folders: list[str]):
        """检测结果返回"""
        has_custom = len(folders) > 0
        self._has_custom_folders = has_custom

        if has_custom:
            self._release_container.setVisible(True)

        # 继续获取标准版本列表
        self._fetch_versions()

    def _on_check_folders_error(self, msg: str):
        """检测失败，默认不显示切换按钮，直接获取标准版本"""
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
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_status.setText("正在获取版本列表...")
        self.refresh_btn.setEnabled(False)

        self._fetch_worker = FetchVersionsWorker(self._username, self._password)
        self._fetch_worker.success.connect(self._on_versions_loaded)
        self._fetch_worker.error.connect(self._on_versions_error)
        self._fetch_worker.start()

    def _fetch_custom_folders(self):
        """启动后台定制文件夹获取（定制发布）"""
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_status.setText("正在获取定制文件夹列表...")
        self.refresh_btn.setEnabled(False)

        self._fetch_custom_worker = FetchCustomFoldersWorker(self._username, self._password)
        self._fetch_custom_worker.success.connect(self._on_custom_folders_loaded)
        self._fetch_custom_worker.error.connect(self._on_custom_folders_error)
        self._fetch_custom_worker.start()

    def _on_versions_loaded(self, versions: list[str]):
        self._versions = versions
        self.version_combo.clear()
        self.version_combo.addItems(versions)
        self.version_combo.setEnabled(True)
        self.version_status.setText(f"找到 {len(versions)} 个版本（最新: {versions[0]}）")
        self.refresh_btn.setEnabled(True)

    def _on_versions_error(self, msg: str):
        self.version_status.setText(f"获取失败: {msg}")
        self.refresh_btn.setEnabled(True)
        QMessageBox.warning(self, "获取版本失败", msg)

    def _on_custom_folders_loaded(self, folders: list[str]):
        self._versions = folders
        self.version_combo.clear()
        self.version_combo.addItems(folders)
        self.version_combo.setEnabled(True)
        self.version_status.setText(f"找到 {len(folders)} 个定制文件夹")
        self.refresh_btn.setEnabled(True)

    def _on_custom_folders_error(self, msg: str):
        self.version_status.setText(f"获取失败: {msg}")
        self.refresh_btn.setEnabled(True)
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
