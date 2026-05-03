"""向导主窗口：QStackedWidget 管理四个页面切换"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.components import SidebarStepItem
from downloader.ui.config_page import ConfigPage
from downloader.ui.download_page import DownloadPage
from downloader.ui.mode_selection_page import ModeSelectionPage
from downloader.ui.theme import Colors, font
from downloader.ui.welcome_page import WelcomePage


class WizardWindow(QWidget):
    """向导主窗口"""

    def __init__(self):
        super().__init__()
        self._username = ""
        self._password = ""
        self._selected_arch = ""
        self._selected_version = ""
        self._selected_os = ""
        self._release_type = "standard"
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("登临部署包下载工具V0.2")
        self.setMinimumSize(860, 600)
        self.resize(940, 640)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # 页面堆栈
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {Colors.PAGE_BG};")
        main_layout.addWidget(self.stack, 1)

        # 创建四个页面
        self.welcome_page = WelcomePage()
        self.config_page = ConfigPage()
        self.mode_page = ModeSelectionPage()
        self.download_page = DownloadPage()

        self.stack.addWidget(self.welcome_page)    # 0
        self.stack.addWidget(self.config_page)     # 1
        self.stack.addWidget(self.mode_page)       # 2
        self.stack.addWidget(self.download_page)   # 3

        # 连接信号
        self.welcome_page.start_clicked.connect(self._go_to_config)
        self.config_page.next_clicked.connect(self._go_to_mode_selection)
        self.config_page.back_clicked.connect(self._go_to_welcome)
        self.mode_page.next_clicked.connect(self._go_to_download)
        self.mode_page.back_clicked.connect(self._go_to_config)
        self.download_page.back_clicked.connect(self._go_to_mode_selection_back)

        # 初始状态
        self._update_steps(0)

    def _create_sidebar(self) -> QWidget:
        """创建品牌侧边栏"""
        sidebar = QWidget()
        sidebar.setFixedWidth(236)
        sidebar.setStyleSheet(f"background-color: {Colors.SIDEBAR};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(24, 28, 24, 22)
        layout.setSpacing(0)

        brand_label = QLabel("DengLin")
        brand_label.setFont(font(20))
        brand_label.setStyleSheet(f"color: {Colors.SURFACE};")
        layout.addWidget(brand_label)

        app_name_label = QLabel("部署包下载工具")
        app_name_label.setFont(font(10))
        app_name_label.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
        layout.addWidget(app_name_label)

        version_label = QLabel("V0.2")
        version_label.setFont(font(9))
        version_label.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
        layout.addWidget(version_label)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {Colors.SIDEBAR_CARD};")
        layout.addSpacing(22)
        layout.addWidget(divider)
        layout.addSpacing(22)

        self._sidebar_steps: list[SidebarStepItem] = []
        for number, title in enumerate(
            ["连接服务器", "发布配置", "选择内容", "下载任务"], start=1
        ):
            step_item = SidebarStepItem(number, title)
            self._sidebar_steps.append(step_item)
            layout.addWidget(step_item)
            layout.addSpacing(16)

        layout.addStretch(1)

        summary_title = QLabel("当前任务")
        summary_title.setFont(font(10))
        summary_title.setStyleSheet(f"color: {Colors.SIDEBAR_MUTED};")
        layout.addWidget(summary_title)

        self._sidebar_summary = QLabel()
        self._sidebar_summary.setFont(font(10))
        self._sidebar_summary.setWordWrap(True)
        self._sidebar_summary.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._sidebar_summary.setStyleSheet(
            f"color: {Colors.SURFACE}; line-height: 150%;"
        )
        layout.addSpacing(8)
        layout.addWidget(self._sidebar_summary)

        return sidebar

    def _update_steps(self, current: int):
        """更新步骤指示器状态"""
        for i, step_item in enumerate(self._sidebar_steps):
            if i < current:
                step_item.set_state("done")
            elif i == current:
                step_item.set_state("current")
            else:
                step_item.set_state("pending")
        self._update_sidebar_summary(current)

    def _update_sidebar_summary(self, current: int):
        """更新侧边栏当前任务摘要"""
        if current == 0:
            summary = "等待连接服务器"
        elif current == 1:
            summary = f"账号: {self._username or '-'}"
        elif current == 2:
            version = self._selected_version or "-"
            if self._release_type == "custom":
                summary = f"定制发布\n版本: {version}"
            else:
                arch = self._selected_arch or "-"
                os_name = self._selected_os or "-"
                summary = f"标准发布\n{arch} / {os_name} / {version}"
        elif current == 3:
            summary = "准备下载所选文件"
        else:
            summary = ""
        self._sidebar_summary.setText(summary)

    def _go_to_welcome(self):
        self.stack.setCurrentIndex(0)
        self._update_steps(0)

    def _go_to_config(self, username: str = "", password: str = ""):
        self._username = username
        self._password = password
        self.stack.setCurrentIndex(1)
        self._update_steps(1)
        self.config_page.on_enter(username, password)

    def _go_to_mode_selection(self, arch: str, version: str, os_name: str,
                              release_type: str = "standard"):
        self._selected_arch = arch
        self._selected_version = version
        self._selected_os = os_name
        self._release_type = release_type
        self.stack.setCurrentIndex(2)
        self._update_steps(2)
        self.mode_page.on_enter(
            arch, version, os_name, self._username, self._password, release_type
        )

    def _go_to_download(self, mode_config: dict):
        self.stack.setCurrentIndex(3)
        self._update_steps(3)
        self.download_page.on_enter(
            self._selected_arch,
            self._selected_version,
            self._username,
            self._password,
            mode_config,
            self._selected_os,
            self._release_type,
        )

    def _go_to_mode_selection_back(self):
        """从下载页返回模式选择页"""
        self.stack.setCurrentIndex(2)
        self._update_steps(2)
        self.mode_page.on_enter(
            self._selected_arch, self._selected_version,
            self._selected_os, self._username, self._password,
            self._release_type,
        )
