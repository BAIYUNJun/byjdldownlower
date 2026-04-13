"""向导页面 1：欢迎页"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader.config import SFTP_HOST, SFTP_PORT


class WelcomePage(QWidget):
    """欢迎页：工具名称、服务器信息、开始按钮"""

    start_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(60, 80, 60, 40)

        # 垂直弹簧，顶部居中
        layout.addStretch(1)

        # 工具名称
        title = QLabel("DengLin vLLM")
        title.setFont(QFont("Microsoft YaHei", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("部署包下载工具")
        subtitle.setFont(QFont("Microsoft YaHei", 20))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666666;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #DDDDDD;")
        layout.addWidget(line)

        layout.addSpacing(10)

        # 服务器信息
        info_label = QLabel(f"SFTP 服务器: {SFTP_HOST}:{SFTP_PORT}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(info_label)

        # 垂直弹簧
        layout.addStretch(1)

        # 开始按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.start_btn = QPushButton("开  始")
        self.start_btn.setFixedSize(200, 48)
        self.start_btn.setFont(QFont("Microsoft YaHei", 14))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3A7BC8;
            }
            QPushButton:pressed {
                background-color: #2E6AB5;
            }
        """)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        layout.addStretch(1)
