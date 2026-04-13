"""QThread 工作线程：版本获取、文件下载"""

import os

from PyQt6.QtCore import QThread, pyqtSignal

from downloader.sftp_client import SFTPClient


class FetchVersionsWorker(QThread):
    """后台获取可用 SDK 版本列表"""

    success = pyqtSignal(list)   # versions: list[str]
    error = pyqtSignal(str)      # error_message: str

    def run(self):
        try:
            client = SFTPClient()
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

    def __init__(self, version: str, arch: str):
        super().__init__()
        self.version = version
        self.arch = arch

    def run(self):
        try:
            client = SFTPClient()
            client.connect()
            try:
                all_files = client.get_remote_file_list(self.version)
                matches = client.filter_matches(all_files, self.arch)
                self.success.emit(matches, all_files)
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

    def __init__(self, version: str, files: list[str], save_dir: str):
        super().__init__()
        self.version = version
        self.files = files
        self.save_dir = save_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            client = SFTPClient()
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
                    )
                    self.file_completed.emit(filename)
                    self.overall_progress.emit(i + 1, total)

                self.log_message.emit("所有文件下载完成!")
                self.all_done.emit()
            finally:
                client.disconnect()
        except Exception as e:
            self.error.emit(f"下载失败: {e}")
