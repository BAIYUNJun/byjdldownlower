"""向导主窗口：QStackedWidget 管理四个页面切换"""

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

from downloader.ui.config_page import ConfigPage
from downloader.ui.download_page import DownloadPage
from downloader.ui.mode_selection_page import ModeSelectionPage
from downloader.ui.welcome_page import WelcomePage


class WizardWindow(QWidget):
    """向导主窗口"""

    def __init__(self):
        super().__init__()
        self._username = ""
        self._password = ""
        self._selected_arch = ""
        self._selected_version = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("DengLin vLLM 部署包下载工具")
        self.setMinimumSize(700, 560)
        self.resize(700, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 步骤指示器
        self._step_bar = self._create_step_bar()
        main_layout.addWidget(self._step_bar)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #DDDDDD; max-height: 1px;")
        main_layout.addWidget(line)

        # 页面堆栈
        self.stack = QStackedWidget()
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

    def _create_step_bar(self) -> QWidget:
        """创建步骤指示器"""
        bar = QWidget()
        bar.setFixedHeight(50)
        bar.setStyleSheet("background-color: #F8F8F8;")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 0, 40, 0)

        self._step_labels: list[QLabel] = []
        steps = ["欢迎", "配置", "选择模式", "下载"]
        for i, name in enumerate(steps):
            step_widget = QWidget()
            step_layout = QVBoxLayout(step_widget)
            step_layout.setSpacing(2)
            step_layout.setContentsMargins(0, 4, 0, 4)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            circle = QLabel(str(i + 1))
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFixedSize(28, 28)
            circle.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            circle.setStyleSheet("""
                background-color: #DDDDDD;
                color: #888888;
                border-radius: 14px;
            """)
            step_layout.addWidget(circle, 0, Qt.AlignmentFlag.AlignHCenter)

            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setStyleSheet("color: #888888;")
            step_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)

            layout.addWidget(step_widget, 1)
            self._step_labels.append(circle)

            if i < len(steps) - 1:
                connector = QFrame()
                connector.setFrameShape(QFrame.Shape.HLine)
                connector.setFixedHeight(2)
                connector.setStyleSheet("background-color: #DDDDDD;")
                layout.addWidget(connector, 1)

        return bar

    def _update_steps(self, current: int):
        """更新步骤指示器状态"""
        for i, circle in enumerate(self._step_labels):
            if i < current:
                circle.setStyleSheet("""
                    background-color: #4A90D9;
                    color: white;
                    border-radius: 14px;
                """)
            elif i == current:
                circle.setStyleSheet("""
                    background-color: #4A90D9;
                    color: white;
                    border-radius: 14px;
                """)
            else:
                circle.setStyleSheet("""
                    background-color: #DDDDDD;
                    color: #888888;
                    border-radius: 14px;
                """)

    def _go_to_welcome(self):
        self.stack.setCurrentIndex(0)
        self._update_steps(0)

    def _go_to_config(self, username: str = "", password: str = ""):
        self._username = username
        self._password = password
        self.stack.setCurrentIndex(1)
        self._update_steps(1)
        self.config_page.on_enter(username, password)

    def _go_to_mode_selection(self, arch: str, version: str):
        self._selected_arch = arch
        self._selected_version = version
        self.stack.setCurrentIndex(2)
        self._update_steps(2)
        self.mode_page.on_enter(arch, version, self._username, self._password)

    def _go_to_download(self, mode_config: dict):
        self.stack.setCurrentIndex(3)
        self._update_steps(3)
        self.download_page.on_enter(
            self._selected_arch,
            self._selected_version,
            self._username,
            self._password,
            mode_config,
        )

    def _go_to_mode_selection_back(self):
        """从下载页返回模式选择页"""
        self._go_to_mode_selection(self._selected_arch, self._selected_version)
