"""向导页面 4：文件列表 + 下载进度 + 日志"""

from __future__ import annotations

import os
import subprocess
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.components import ElidedLabel, PageHeader
from downloader.ui.theme import Colors, button_style, font, input_style
from downloader.workers import DownloadWorker, FetchFilesWorker


class DownloadPage(QWidget):
    """下载页：显示匹配文件、选择保存目录、下载进度"""

    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._arch = ""
        self._version = ""
        self._username = ""
        self._password = ""
        self._category_labels: dict[str, str] = {}
        self._matches: dict[str, list[str]] = {}
        self._all_files: list[str] = []
        self._download_worker: DownloadWorker | None = None
        self._download_start_time: float = 0
        self._current_file_start_time: float = 0
        self._current_file_transferred: int = 0
        self._release_type: str = "standard"
        self._failed_files: list[tuple[str, str]] = []
        self._completed_files: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(44, 34, 44, 28)

        layout.addWidget(PageHeader("下载任务", "确认文件列表、保存目录和下载进度"))

        # 匹配的文件列表
        self.file_list_label = QLabel("匹配到的文件")
        self.file_list_label.setFont(font(11, QFont.Weight.Bold))
        self.file_list_label.setStyleSheet(f"color: {Colors.TEXT};")
        layout.addWidget(self.file_list_label)

        self.file_list_area = QScrollArea()
        self.file_list_area.setWidgetResizable(True)
        self.file_list_area.setMinimumHeight(96)
        self.file_list_area.setMaximumHeight(150)
        self.file_list_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {Colors.SURFACE};
            }}
            QScrollBar:vertical {{
                background: {Colors.SURFACE_MUTED};
                width: 10px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_HOVER};
                border-radius: 4px;
            }}
        """)
        self.file_list_content = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_content)
        self.file_list_layout.setSpacing(4)
        self.file_list_layout.setContentsMargins(10, 8, 10, 8)
        self.file_list_area.setWidget(self.file_list_content)
        layout.addWidget(self.file_list_area)

        # 保存目录
        dir_layout = QHBoxLayout()
        dir_layout.setSpacing(10)
        dir_label = QLabel("保存到:")
        dir_label.setFont(font(10, QFont.Weight.Bold))
        dir_label.setStyleSheet(f"color: {Colors.TEXT};")
        dir_layout.addWidget(dir_label)

        self.dir_edit = QLineEdit()
        self.dir_edit.setFont(font(10))
        self.dir_edit.setMinimumHeight(38)
        self.dir_edit.setStyleSheet(input_style())
        self.dir_edit.setPlaceholderText("请选择保存目录...")
        dir_layout.addWidget(self.dir_edit, 1)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFont(font(10, QFont.Weight.Bold))
        self.browse_btn.setMinimumSize(74, 38)
        self.browse_btn.setStyleSheet(button_style("secondary"))
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.browse_btn)
        layout.addLayout(dir_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #DDDDDD;")
        layout.addWidget(line)

        # 进度区域
        # 总体进度
        overall_layout = QHBoxLayout()
        overall_layout.setSpacing(10)
        self.overall_label = QLabel("总进度:")
        self.overall_label.setFont(font(10, QFont.Weight.Bold))
        self.overall_label.setStyleSheet(f"color: {Colors.TEXT};")
        overall_layout.addWidget(self.overall_label)
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        overall_layout.addWidget(self.overall_progress, 1)
        layout.addLayout(overall_layout)

        # 当前文件进度
        self.current_file_label = ElidedLabel("当前文件: -")
        self.current_file_label.setFont(font(10))
        self.current_file_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self.current_file_label)

        file_layout = QHBoxLayout()
        file_layout.setSpacing(10)

        self.file_progress = QProgressBar()
        self.file_progress.setTextVisible(True)
        file_layout.addWidget(self.file_progress, 1)

        self.speed_label = QLabel("")
        self.speed_label.setFont(font(9))
        self.speed_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        self.speed_label.setFixedWidth(120)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        file_layout.addWidget(self.speed_label)
        layout.addLayout(file_layout)

        # 日志区域
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 10))
        self.log_box.setMaximumHeight(160)
        self.log_box.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {Colors.LOG_BG};
                color: {Colors.LOG_TEXT};
                border: none;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self.log_box, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.back_btn = QPushButton("上一步")
        self.back_btn.setMinimumSize(104, 40)
        self.back_btn.setFont(font(10))
        self.back_btn.setStyleSheet(button_style("secondary"))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.download_btn = QPushButton("开始下载")
        self.download_btn.setMinimumSize(124, 40)
        self.download_btn.setFont(font(10, QFont.Weight.Bold))
        self.download_btn.setStyleSheet(button_style("primary"))
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self._start_download)

        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.setMinimumSize(112, 40)
        self.open_folder_btn.setFont(font(10, QFont.Weight.Bold))
        self.open_folder_btn.setStyleSheet(button_style("success"))
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setVisible(False)

        btn_layout.addWidget(self.back_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.download_btn)
        layout.addLayout(btn_layout)

    def on_enter(
        self,
        arch: str,
        version: str,
        username: str,
        password: str,
        mode_config: dict,
        os_name: str = "",
        release_type: str = "standard",
    ):
        """进入下载页时，获取文件列表或直接使用定制文件"""
        self._arch = arch
        self._version = version
        self._username = username
        self._password = password
        self._release_type = release_type
        self._category_labels = mode_config.get("category_labels", {})
        self._reset_state()

        if release_type == "custom":
            # 定制模式：文件列表已从模式选择页获取，直接使用
            files = mode_config.get("files", [])
            self._matches = {"custom": files}
            self._all_files = files
            self._show_file_list(files)
            if files:
                self._log(f"共 {len(files)} 个文件待下载")
                self.download_btn.setEnabled(True)
            else:
                self._log("未找到文件")
        else:
            # 标准模式：后台获取并过滤
            selected_categories = mode_config.get("categories", [])
            self._log(f"正在获取 {version} 版本的文件列表...")
            self.download_btn.setEnabled(False)

            self._fetch_worker = FetchFilesWorker(
                version, arch, username, password, selected_categories, os_name
            )
            self._fetch_worker.success.connect(self._on_files_loaded)
            self._fetch_worker.error.connect(self._on_files_error)
            self._fetch_worker.start()

    def _reset_state(self):
        self._matches = {}
        self._all_files = []
        self._clear_file_list()
        self._failed_files = []
        self._completed_files = []
        self.overall_progress.setValue(0)
        self.file_progress.setValue(0)
        self.current_file_label.setText("当前文件: -")
        self.speed_label.setText("")
        self.log_box.clear()
        self.open_folder_btn.setVisible(False)
        self.download_btn.setText("开始下载")
        self.download_btn.setEnabled(True)

    def _on_files_loaded(self, matches: dict, all_files: list):
        self._matches = matches
        self._all_files = all_files

        self._clear_file_list()
        total = 0
        for cat_key, files in matches.items():
            label = self._category_labels.get(cat_key, cat_key)
            total += len(files)
            for f in files:
                item = ElidedLabel(f"[{label}] {os.path.basename(f)}")
                item.setFont(font(10))
                item.setMinimumHeight(22)
                item.setStyleSheet(f"color: {Colors.TEXT};")
                self.file_list_layout.addWidget(item)

        if total == 0:
            no_match = QLabel("未找到匹配文件。所有远程文件:")
            no_match.setFont(font(10, QFont.Weight.Bold))
            no_match.setStyleSheet(f"color: {Colors.ERROR};")
            self.file_list_layout.addWidget(no_match)
            for f in all_files[:20]:
                item = ElidedLabel(f)
                item.setFont(font(10))
                item.setMinimumHeight(22)
                item.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
                self.file_list_layout.addWidget(item)
            self._log(f"警告: 未匹配到文件。远程共 {len(all_files)} 个文件。")
        else:
            self._log(f"找到 {total} 个匹配文件")
            self.download_btn.setEnabled(True)

    def _show_file_list(self, files: list[str]):
        """显示文件列表到UI（定制模式使用）"""
        self._clear_file_list()
        for f in files:
            item = ElidedLabel(os.path.basename(f))
            item.setFont(font(10))
            item.setMinimumHeight(22)
            item.setStyleSheet(f"color: {Colors.TEXT};")
            self.file_list_layout.addWidget(item)

    def _on_files_error(self, msg: str):
        self._log(f"错误: {msg}")
        QMessageBox.warning(self, "获取文件列表失败", msg)

    def _clear_file_list(self):
        while self.file_list_layout.count():
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if path:
            self.dir_edit.setText(path)

    def _start_download(self):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
            self.download_btn.setText("开始下载")
            self.download_btn.setEnabled(True)
            return

        save_dir = self.dir_edit.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "请选择目录", "请先选择文件保存目录")
            return
        if not os.path.isdir(save_dir):
            QMessageBox.warning(self, "目录无效", "选择的目录不存在")
            return

        if self._failed_files:
            all_matched = self._reconstruct_remote_paths(
                [f[0] for f in self._failed_files]
            )
            self._failed_files = []
        else:
            all_matched = []
            for files in self._matches.values():
                all_matched.extend(files)

        if not all_matched:
            QMessageBox.warning(self, "无文件", "没有匹配的文件可下载")
            return

        self._download_start_time = time.time()
        self._current_file_start_time = time.time()
        self._current_file_transferred = 0
        self.download_btn.setText("取消下载")
        self.overall_progress.setMaximum(len(all_matched))

        self._download_worker = DownloadWorker(
            self._version, all_matched, save_dir, self._username, self._password,
            is_custom=getattr(self, "_release_type", "standard") == "custom",
        )
        self._download_worker.file_progress.connect(self._on_file_progress)
        self._download_worker.overall_progress.connect(self._on_overall_progress)
        self._download_worker.file_completed.connect(self._on_file_completed)
        self._download_worker.file_failed.connect(self._on_file_failed)
        self._download_worker.log_message.connect(self._log)
        self._download_worker.all_done.connect(self._on_all_done)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_file_progress(self, filename: str, transferred: int, total: int):
        self.current_file_label.setText(f"当前文件: {filename}")
        if total > 0:
            self.file_progress.setMaximum(total)
            self.file_progress.setValue(transferred)
            pct = transferred / total * 100
            self.file_progress.setFormat(f"{pct:.1f}%")

            elapsed = time.time() - self._current_file_start_time
            if elapsed > 0.5 and transferred > self._current_file_transferred:
                speed = (transferred - self._current_file_transferred) / elapsed
                if speed > 0:
                    self.speed_label.setText(self._format_size(speed) + "/s")
                self._current_file_start_time = time.time()
                self._current_file_transferred = transferred

    def _on_overall_progress(self, completed: int, total: int):
        self.overall_progress.setValue(completed)
        self.overall_progress.setFormat(f"{completed}/{total}")

    def _on_file_completed(self, filename: str):
        self._log(f"✓ {filename} 下载完成")
        self._current_file_start_time = time.time()
        self._current_file_transferred = 0

    def _on_file_failed(self, filename: str, error_msg: str):
        self._log(f"✗ {filename} 下载失败: {error_msg}")

    def _on_all_done(self):
        if self._download_worker:
            self._failed_files = self._download_worker.failed_files
            self._completed_files = self._download_worker.completed_files

        if self._failed_files:
            self.download_btn.setText("重试失败文件")
            self.download_btn.setEnabled(True)
            self.open_folder_btn.setVisible(True)
            self.speed_label.setText("")
            failed_names = "\n".join(f"  - {f[0]}" for f in self._failed_files)
            QMessageBox.warning(
                self, "部分文件下载失败",
                f"以下文件下载失败:\n{failed_names}\n\n"
                f"点击\"重试失败文件\"按钮重新下载。"
            )
        else:
            self.download_btn.setText("已完成")
            self.download_btn.setEnabled(False)
            self.open_folder_btn.setVisible(True)
            self.speed_label.setText("")
            QMessageBox.information(self, "下载完成", "所有文件已下载完成!")

    def _on_download_error(self, msg: str):
        self._log(f"错误: {msg}")
        self.download_btn.setText("重试下载")
        self.download_btn.setEnabled(True)
        QMessageBox.critical(self, "下载失败", msg)

    def _reconstruct_remote_paths(self, filenames: list[str]) -> list[str]:
        name_to_path = {}
        for files in self._matches.values():
            for f in files:
                name_to_path[os.path.basename(f)] = f
        result = []
        for fn in filenames:
            if fn in name_to_path:
                result.append(name_to_path[fn])
            else:
                result.append(fn)
        return result

    def _open_folder(self):
        path = self.dir_edit.text().strip()
        if path and os.path.isdir(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["open", path])

    def _log(self, message: str):
        self.log_box.appendPlainText(message)

    @staticmethod
    def _format_size(bytes_size: float) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
