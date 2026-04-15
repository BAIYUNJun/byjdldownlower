"""QThread 工作线程：版本获取、文件下载"""

from __future__ import annotations

import os

from PyQt6.QtCore import QThread, pyqtSignal

from downloader.sftp_client import SFTPClient


class FetchVersionsWorker(QThread):
    """后台获取可用 SDK 版本列表"""

    success = pyqtSignal(list)   # versions: list[str]
    error = pyqtSignal(str)      # error_message: str

    def __init__(self, username: str, password: str):
        super().__init__()
        self._username = username
        self._password = password

    def run(self):
        try:
            client = SFTPClient(self._username, self._password)
            client.connect()
            try:
                versions = client.get_available_versions()
                if not versions:
                    self.error.emit("未找到可用版本")
                else:
                    self.success.emit(versions)
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"连接服务器失败: {e}")


class FetchFilesWorker(QThread):
    """后台获取指定版本的文件列表并过滤"""

    success = pyqtSignal(dict, list)  # matches: dict, all_files: list
    error = pyqtSignal(str)

    def __init__(
        self,
        version: str,
        arch: str,
        username: str,
        password: str,
        selected_categories: list[str] | None = None,
        os_name: str = "",
    ):
        super().__init__()
        self.version = version
        self.arch = arch
        self._username = username
        self._password = password
        self.selected_categories = selected_categories
        self.os_name = os_name

    def run(self):
        try:
            client = SFTPClient(self._username, self._password)
            client.connect()
            try:
                all_files = client.get_remote_file_list(self.version)
                if self.selected_categories is not None:
                    matches = client.filter_custom(
                        all_files, self.arch, self.selected_categories, self.os_name
                    )
                else:
                    matches = {}
                self.success.emit(matches, all_files)
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"获取文件列表失败: {e}")


class FetchCustomFoldersWorker(QThread):
    """后台获取根目录下的定制发布文件夹列表"""

    success = pyqtSignal(list)   # folders: list[str]
    error = pyqtSignal(str)

    def __init__(self, username: str, password: str):
        super().__init__()
        self._username = username
        self._password = password

    def run(self):
        try:
            client = SFTPClient(self._username, self._password)
            client.connect()
            try:
                folders = client.get_custom_folders()
                if not folders:
                    self.error.emit("未找到定制发布文件夹")
                else:
                    self.success.emit(folders)
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"获取定制文件夹失败: {e}")


class FetchCustomFilesWorker(QThread):
    """后台获取定制文件夹内的文件列表"""

    success = pyqtSignal(list)   # files: list[str]
    error = pyqtSignal(str)

    def __init__(self, username: str, password: str, folder: str):
        super().__init__()
        self._username = username
        self._password = password
        self._folder = folder

    def run(self):
        try:
            client = SFTPClient(self._username, self._password)
            client.connect()
            try:
                files = client.get_custom_files(self._folder)
                if not files:
                    self.error.emit("该文件夹下未找到文件")
                else:
                    self.success.emit(files)
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"获取文件列表失败: {e}")


class DownloadWorker(QThread):
    """后台下载文件"""

    file_progress = pyqtSignal(str, int, int)  # filename, transferred, total
    overall_progress = pyqtSignal(int, int)     # completed_count, total_count
    file_completed = pyqtSignal(str)            # filename
    log_message = pyqtSignal(str)               # message
    all_done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self, version: str, files: list[str], save_dir: str,
        username: str, password: str, is_custom: bool = False,
    ):
        super().__init__()
        self.version = version
        self.files = files
        self.save_dir = save_dir
        self._username = username
        self._password = password
        self._is_custom = is_custom
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            client = SFTPClient(self._username, self._password)
            client.connect()
            try:
                total = len(self.files)
                for i, file_path in enumerate(self.files):
                    if self._cancelled:
                        self.log_message.emit("下载已取消")
                        return

                    filename = os.path.basename(file_path)
                    self.log_message.emit(f"正在下载 ({i + 1}/{total}): {filename}")

                    def progress_cb(transferred: int, total_bytes: int, fn=filename):
                        self.file_progress.emit(fn, transferred, total_bytes)

                    client.download_file(
                        file_path,
                        self.save_dir,
                        self.version,
                        progress_callback=progress_cb,
                        is_custom=self._is_custom,
                    )
                    self.file_completed.emit(filename)
                    self.overall_progress.emit(i + 1, total)

                self.log_message.emit("所有文件下载完成!")
                self.all_done.emit()
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"下载失败: {e}")
