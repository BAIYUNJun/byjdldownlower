"""向导页面 1：欢迎页"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader import credentials
from downloader.config import SFTP_HOST, SFTP_PORT


class WelcomePage(QWidget):
    """欢迎页：凭据输入、服务器信息、开始按钮"""

    start_clicked = pyqtSignal(str, str)  # username, password

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._auto_fill_credentials()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(60, 60, 60, 40)

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

        layout.addSpacing(16)

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

        layout.addSpacing(16)

        # 凭据输入区域（居中）
        cred_container = QVBoxLayout()
        cred_container.setSpacing(10)
        cred_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 用户名
        cred_container.addWidget(self._make_label("用户名"))
        self.username_edit = QLineEdit()
        self.username_edit.setFixedWidth(300)
        self.username_edit.setFixedHeight(36)
        self.username_edit.setFont(QFont("Microsoft YaHei", 11))
        self.username_edit.setPlaceholderText("请输入用户名")
        self.username_edit.textChanged.connect(self._validate_inputs)
        cred_container.addWidget(self.username_edit, 0, Qt.AlignmentFlag.AlignHCenter)

        # 密码
        cred_container.addWidget(self._make_label("密码"))
        self.password_edit = QLineEdit()
        self.password_edit.setFixedWidth(300)
        self.password_edit.setFixedHeight(36)
        self.password_edit.setFont(QFont("Microsoft YaHei", 11))
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.textChanged.connect(self._validate_inputs)
        cred_container.addWidget(self.password_edit, 0, Qt.AlignmentFlag.AlignHCenter)

        # 记住密码
        self.remember_cb = QCheckBox("记住密码")
        self.remember_cb.setFont(QFont("Microsoft YaHei", 10))
        self.remember_cb.setStyleSheet("color: #666666;")
        cred_container.addWidget(self.remember_cb, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addLayout(cred_container)

        # 垂直弹簧
        layout.addStretch(1)

        # 开始按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.start_btn = QPushButton("开  始")
        self.start_btn.setFixedSize(200, 48)
        self.start_btn.setFont(QFont("Microsoft YaHei", 14))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setEnabled(False)
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
            QPushButton:disabled {
                background-color: #AAAAAA;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        layout.addStretch(1)

    @staticmethod
    def _make_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Microsoft YaHei", 11))
        label.setStyleSheet("color: #444444;")
        return label

    def _auto_fill_credentials(self):
        """从 QSettings 加载已保存的凭据"""
        saved = credentials.load_credentials()
        if saved:
            username, password = saved
            self.username_edit.setText(username)
            self.password_edit.setText(password)
            self.remember_cb.setChecked(True)

    def _validate_inputs(self):
        """两个字段都有内容时启用开始按钮"""
        valid = bool(self.username_edit.text().strip()) and bool(self.password_edit.text().strip())
        self.start_btn.setEnabled(valid)

    def _on_start(self):
        """点击开始：保存/清除凭据，发射信号"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if self.remember_cb.isChecked():
            credentials.save_credentials(username, password)
        else:
            credentials.clear_credentials()
        self.start_clicked.emit(username, password)
