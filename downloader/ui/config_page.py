"""向导页面 2：架构选择 + 版本选择"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.workers import FetchVersionsWorker


class ArchCardButton(QPushButton):
    """架构选择卡片按钮"""

    def __init__(self, label: str, desc: str, parent=None):
        super().__init__(parent)
        self.label = label
        self.desc = desc
        self.setFixedSize(200, 100)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
    """配置页：选择架构和版本"""

    next_clicked = pyqtSignal(str, str)   # arch, version
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._versions: list[str] = []
        self._fetch_worker: FetchVersionsWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(60, 40, 60, 40)

        # 架构选择
        arch_title = QLabel("请选择 CPU 架构")
        arch_title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(arch_title)

        arch_layout = QHBoxLayout()
        arch_layout.setSpacing(20)

        self.x86_btn = ArchCardButton("x86_64", "Intel / AMD 64位")
        self.x86_btn.setText("x86_64\nIntel / AMD 64位")
        self.x86_btn.setFont(QFont("Microsoft YaHei", 11))

        self.arm64_btn = ArchCardButton("arm64", "ARM 64位")
        self.arm64_btn.setText("arm64\nARM 64位 (aarch64)")
        self.arm64_btn.setFont(QFont("Microsoft YaHei", 11))

        self._arch_group = QButtonGroup(self)
        self._arch_group.addButton(self.x86_btn)
        self._arch_group.addButton(self.arm64_btn)

        arch_layout.addStretch(1)
        arch_layout.addWidget(self.x86_btn)
        arch_layout.addWidget(self.arm64_btn)
        arch_layout.addStretch(1)
        layout.addLayout(arch_layout)

        layout.addSpacing(20)

        # 版本选择
        ver_title = QLabel("选择 SDK 版本")
        ver_title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(ver_title)

        ver_layout = QHBoxLayout()
        self.version_combo = QComboBox()
        self.version_combo.setFont(QFont("Microsoft YaHei", 11))
        self.version_combo.setMinimumHeight(36)
        self.version_combo.setEnabled(False)
        ver_layout.addWidget(self.version_combo, 1)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(70, 36)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._fetch_versions)
        ver_layout.addWidget(self.refresh_btn)
        layout.addLayout(ver_layout)

        self.version_status = QLabel("")
        self.version_status.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.version_status)

        layout.addStretch(1)

        # 底部按钮
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
        """)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.back_btn)
        btn_layout.addSpacing(12)
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def on_enter(self):
        """页面显示时自动获取版本列表"""
        if not self._versions:
            self._fetch_versions()

    def _fetch_versions(self):
        """启动后台版本获取"""
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_status.setText("正在获取版本列表...")
        self.refresh_btn.setEnabled(False)

        self._fetch_worker = FetchVersionsWorker()
        self._fetch_worker.success.connect(self._on_versions_loaded)
        self._fetch_worker.error.connect(self._on_versions_error)
        self._fetch_worker.start()

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

    def _on_next(self):
        if not self.x86_btn.isChecked() and not self.arm64_btn.isChecked():
            QMessageBox.warning(self, "请选择架构", "请先选择 CPU 架构")
            return
        if self.version_combo.count() == 0:
            QMessageBox.warning(self, "无版本", "请等待版本列表加载完成")
            return

        arch = "x86" if self.x86_btn.isChecked() else "arm64"
        version = self.version_combo.currentText()
        self.next_clicked.emit(arch, version)

    def get_selected_arch(self) -> str:
        return "x86" if self.x86_btn.isChecked() else "arm64"

    def get_selected_version(self) -> str:
        return self.version_combo.currentText()
