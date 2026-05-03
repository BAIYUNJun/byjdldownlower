"""向导页面 1：连接服务器"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from downloader import credentials
from downloader.config import SFTP_HOST, SFTP_PORT
from downloader.ui.components import PageHeader
from downloader.ui.theme import Colors, button_style, font, input_style


class WelcomePage(QWidget):
    """连接页：凭据输入、服务器信息、开始按钮"""

    start_clicked = pyqtSignal(str, str)  # username, password

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._auto_fill_credentials()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(44, 38, 44, 34)

        header = PageHeader("连接服务器", f"SFTP 服务器: {SFTP_HOST}:{SFTP_PORT}")
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

        form_layout.addSpacing(2)

        self.remember_cb = QCheckBox("记住密码")
        self.remember_cb.setFont(font(10))
        self.remember_cb.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        form_layout.addWidget(self.remember_cb, 0, Qt.AlignmentFlag.AlignLeft)

        form_layout.addSpacing(8)

        self.start_btn = QPushButton("连接并继续")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setFont(font(12, QFont.Weight.Bold))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(button_style("primary"))
        self.start_btn.clicked.connect(self._on_start)
        form_layout.addWidget(self.start_btn)

        form_row = QHBoxLayout()
        form_row.setContentsMargins(0, 0, 0, 0)
        form_row.addStretch(1)
        form_row.addWidget(form)
        form_row.addStretch(1)
        layout.addLayout(form_row)

        layout.addStretch(1)

    @staticmethod
    def _make_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(font(10, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {Colors.TEXT};")
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
