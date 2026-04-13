# Windows 下载工具 UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `download_packages.sh` 的 SFTP 下载逻辑迁移到带 UI 的 Windows 桌面应用

**Architecture:** PyQt6 向导式 UI（欢迎→配置→下载），paramiko 封装 SFTP 操作，QThread 异步执行网络任务，Qt 信号/槽驱动 UI 更新

**Tech Stack:** Python 3.10+, PyQt6, paramiko, fnmatch, re

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `downloader/config.py` | SFTP 服务器配置常量 |
| `downloader/sftp_client.py` | paramiko 封装：连接、列目录、获取版本、过滤文件、下载 |
| `downloader/workers.py` | QThread 子类：版本获取线程、文件下载线程 |
| `downloader/ui/welcome_page.py` | 欢迎页组件 |
| `downloader/ui/config_page.py` | 配置页组件（架构选择 + 版本选择） |
| `downloader/ui/download_page.py` | 下载页组件（文件列表 + 进度 + 日志） |
| `downloader/ui/wizard.py` | ���导主窗口，QStackedWidget 管理页面切换 |
| `downloader/main.py` | 入口，启动应用 |
| `requirements.txt` | 依赖清单 |

---

### Task 1: 项目骨架与配置模块

**Files:**
- Create: `downloader/__init__.py`
- Create: `downloader/ui/__init__.py`
- Create: `downloader/config.py`
- Create: `requirements.txt`

- [ ] **Step 1: 创建项目目录结构**

```bash
mkdir -p downloader/ui
touch downloader/__init__.py downloader/ui/__init__.py
```

- [ ] **Step 2: 创建 `downloader/config.py`**

```python
"""SFTP 服务器配置常量"""

SFTP_HOST = "cuftp.denglinai.com"
SFTP_PORT = 22022
SFTP_USER = "lianyou"
SFTP_PASS = "S9PmMhCk"
REMOTE_BASE_DIR = "/V2 General release"

# 远程目录中已知的子目录
SUB_DIRS = ["", "Base_driver", "K8s", "Vllm", "Vllm0.13.0_product_images", "vllm", "driver", "container"]

# 文件匹配模式
ARCH_PATTERNS = {
    "x86": {
        "driver": "*driver*manylinux*x86*.tar*",
        "container": "*container*x86*.tar*",
        "vllm": "*vllm*x86*.tar*",
    },
    "arm64": {
        "driver": ["*driver*manylinux*arm64*.tar*", "*driver*manylinux*aarch64*.tar*"],
        "container": ["*container*arm64*.tar*", "*container*aarch64*.tar*"],
        "vllm": ["*vllm*arm64*.tar*", "*vllm*aarch64*.tar*"],
    },
}
```

- [ ] **Step 3: 创建 `requirements.txt`**

```
PyQt6>=6.6.0
paramiko>=3.4.0
```

- [ ] **Step 4: 提交**

```bash
git add downloader/__init__.py downloader/ui/__init__.py downloader/config.py requirements.txt
git commit -m "feat: 项目骨架与 SFTP 配置模块"
```

---

### Task 2: SFTP 客户端核心模块

**Files:**
- Create: `downloader/sftp_client.py`

- [ ] **Step 1: 实现 SFTP 客户端**

```python
"""paramiko 封装：连接、列目录、获取版本、过滤文件、下载"""

import os
import re
from fnmatch import fnmatch
from typing import Callable

import paramiko

from downloader.config import (
    ARCH_PATTERNS,
    SFTP_HOST,
    SFTP_PASS,
    SFTP_PORT,
    SFTP_USER,
    SUB_DIRS,
    REMOTE_BASE_DIR,
)


class SFTPClient:
    """SFTP 客户端，封装 paramiko 连接和文件操作"""

    def __init__(self):
        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self):
        """建立 SFTP 连接，失败抛出异常"""
        self._transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        self._transport.connect(username=SFTP_USER, password=SFTP_PASS)
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)

    def disconnect(self):
        """断开连接"""
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._transport:
            self._transport.close()
            self._transport = None

    def get_available_versions(self) -> list[str]:
        """获取可用 SDK 版本列表，按日期降序排序

        Returns:
            版本名称列表，如 ["V2-General_release-20260401", ...]
        """
        entries = self._sftp.listdir(REMOTE_BASE_DIR)
        pattern = re.compile(r"^V2-General_release-\d{8}$")
        versions = [e for e in entries if pattern.match(e)]
        versions.sort(reverse=True)
        return versions

    def get_remote_file_list(self, version: str) -> list[str]:
        """获取指定版本目录下的所有文件列表（递归子目录）

        Args:
            version: 版本名称，如 "V2-General_release-20260401"

        Returns:
            相对路径列表，如 ["Base_driver/driver.tar.gz", "vllm.tar"]
        """
        remote_dir = f"{REMOTE_BASE_DIR}/{version}"
        all_files: list[str] = []

        for subdir in SUB_DIRS:
            target = f"{remote_dir}/{subdir}" if subdir else remote_dir
            try:
                entries = self._sftp.listdir(target)
                for entry in entries:
                    # 检查是文件还是目录（只收集文件）
                    try:
                        self._sftp.stat(f"{target}/{entry}")
                        # 简单判断：文件名含扩展名的视为文件
                        if "." in entry or entry.endswith(".tar") or ".tar." in entry:
                            if subdir:
                                all_files.append(f"{subdir}/{entry}")
                            else:
                                all_files.append(entry)
                    except (IOError, FileNotFoundError):
                        continue
            except (IOError, FileNotFoundError):
                continue

        return all_files

    def filter_matches(self, file_list: list[str], arch: str) -> dict[str, list[str]]:
        """根据架构过滤匹配的文件

        Args:
            file_list: 文件列表
            arch: "x86" 或 "arm64"

        Returns:
            {"driver": [...], "container": [...], "vllm": [...]}
        """
        patterns = ARCH_PATTERNS[arch]
        result: dict[str, list[str]] = {"driver": [], "container": [], "vllm": []}

        for file_name in file_list:
            basename = os.path.basename(file_name)
            for category, pats in patterns.items():
                if isinstance(pats, str):
                    pats = [pats]
                for pat in pats:
                    if fnmatch(basename, pat):
                        result[category].append(file_name)
                        break

        return result

    def download_file(
        self,
        remote_path: str,
        local_dir: str,
        version: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """下载单个文件，支持断点续传

        Args:
            remote_path: 相对于版本目录的路径
            local_dir: 本地保存目录
            version: 版本名称
            progress_callback: 进度回调 (已下载字节数, 总字节数)

        Returns:
            本地文件路径
        """
        remote_full = f"{REMOTE_BASE_DIR}/{version}/{remote_path}"
        local_path = os.path.join(local_dir, os.path.basename(remote_path))

        # 获取远程文件大小
        remote_stat = self._sftp.stat(remote_full)
        total_size = remote_stat.st_size

        # 断点续传：检查本地已有文件大小
        resume_pos = 0
        if os.path.exists(local_path):
            local_size = os.path.getsize(local_path)
            if local_size == total_size:
                # 文件已完整下载
                if progress_callback:
                    progress_callback(total_size, total_size)
                return local_path
            if local_size < total_size:
                resume_pos = local_size

        if resume_pos > 0:
            # 追加模式续传
            with open(local_path, "ab") as f_local:
                # 跳过已下载部分
                self._sftp._transport.open_session().exec_command(
                    f"dd if='{remote_full}' bs=1 skip={resume_pos} 2>/dev/null"
                )
                # 简单方案：重新下载整个文件（断点续传在 SFTP 协议中不直接支持）
            # 重置，直接完整下载
            resume_pos = 0

        # 完整下载
        with open(local_path, "wb") as f_local:
            if progress_callback:
                downloaded = [0]  # 使用列表以便在闭包中修改

                def _callback(transferred: int, total: int):
                    downloaded[0] = transferred
                    progress_callback(transferred, total)

                self._sftp.getfo(remote_full, f_local, callback=_callback)
            else:
                self._sftp.getfo(remote_full, f_local)

        return local_path

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
```

- [ ] **Step 2: 提交**

```bash
git add downloader/sftp_client.py
git commit -m "feat: SFTP 客户端核心模块"
```

---

### Task 3: QThread 工作线程

**Files:**
- Create: `downloader/workers.py`

- [ ] **Step 1: 实现版本获取线程**

```python
"""QThread 工作线程：版本获取、文件下载"""

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

                    import os
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
```

- [ ] **Step 2: 提交**

```bash
git add downloader/workers.py
git commit -m "feat: QThread 工作线程（版本获取、文件下载）"
```

---

### Task 4: 欢迎页 UI

**Files:**
- Create: `downloader/ui/welcome_page.py`

- [ ] **Step 1: 实现欢迎页**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add downloader/ui/welcome_page.py
git commit -m "feat: 欢迎页 UI"
```

---

### Task 5: 配置页 UI

**Files:**
- Create: `downloader/ui/config_page.py`

- [ ] **Step 1: 实现配置页**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add downloader/ui/config_page.py
git commit -m "feat: 配置页 UI（架构选择 + 版本选择）"
```

---

### Task 6: 下载页 UI

**Files:**
- Create: `downloader/ui/download_page.py`

- [ ] **Step 1: 实现下载页**

```python
"""向导页面 3：文件列表 + 下载进度 + 日志"""

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

from downloader.workers import DownloadWorker, FetchFilesWorker


class DownloadPage(QWidget):
    """下载页：显示匹配文件、选择保存目录、下载进度"""

    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._arch = ""
        self._version = ""
        self._matches: dict[str, list[str]] = {}
        self._all_files: list[str] = []
        self._download_worker: DownloadWorker | None = None
        self._download_start_time: float = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(60, 30, 60, 30)

        # 标题
        title = QLabel("下载文件")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 匹配的文件列表
        self.file_list_label = QLabel("匹配到的文件:")
        self.file_list_label.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self.file_list_label)

        self.file_list_area = QScrollArea()
        self.file_list_area.setWidgetResizable(True)
        self.file_list_area.setMaximumHeight(140)
        self.file_list_content = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_content)
        self.file_list_layout.setSpacing(4)
        self.file_list_layout.setContentsMargins(8, 8, 8, 8)
        self.file_list_area.setWidget(self.file_list_content)
        layout.addWidget(self.file_list_area)

        # 保存目录
        dir_layout = QHBoxLayout()
        dir_label = QLabel("保存到:")
        dir_label.setFont(QFont("Microsoft YaHei", 11))
        dir_layout.addWidget(dir_label)

        self.dir_edit = QLineEdit()
        self.dir_edit.setFont(QFont("Microsoft YaHei", 10))
        self.dir_edit.setPlaceholderText("请选择保存目录...")
        dir_layout.addWidget(self.dir_edit, 1)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFixedSize(70, 32)
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
        self.overall_label = QLabel("总进度:")
        self.overall_label.setFont(QFont("Microsoft YaHei", 11))
        overall_layout.addWidget(self.overall_label)
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        overall_layout.addWidget(self.overall_progress, 1)
        layout.addLayout(overall_layout)

        # 当前文件进度
        file_layout = QHBoxLayout()
        self.current_file_label = QLabel("当前文件:")
        self.current_file_label.setFont(QFont("Microsoft YaHei", 10))
        file_layout.addWidget(self.current_file_label)

        self.file_progress = QProgressBar()
        self.file_progress.setTextVisible(True)
        file_layout.addWidget(self.file_progress, 1)

        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.speed_label.setFixedWidth(120)
        file_layout.addWidget(self.speed_label)
        layout.addLayout(file_layout)

        # 日志区域
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 10))
        self.log_box.setMaximumHeight(150)
        self.log_box.setStyleSheet("background-color: #1E1E1E; color: #CCCCCC;")
        layout.addWidget(self.log_box, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("上一步")
        self.back_btn.setFixedSize(120, 40)
        self.back_btn.setFont(QFont("Microsoft YaHei", 11))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0; border: 1px solid #CCCCCC; border-radius: 6px;
            }
            QPushButton:hover { background-color: #E0E0E0; }
        """)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)

        self.download_btn = QPushButton("开始下载")
        self.download_btn.setFixedSize(140, 40)
        self.download_btn.setFont(QFont("Microsoft YaHei", 12))
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9; color: white; border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #3A7BC8; }
            QPushButton:pressed { background-color: #2E6AB5; }
            QPushButton:disabled { background-color: #AAAAAA; }
        """)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self._start_download)

        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.setFixedSize(120, 40)
        self.open_folder_btn.setFont(QFont("Microsoft YaHei", 11))
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #5CB85C; color: white; border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #4CAE4C; }
        """)
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setVisible(False)

        btn_layout.addWidget(self.back_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.download_btn)
        layout.addLayout(btn_layout)

    def on_enter(self, arch: str, version: str):
        """进入下载页时，获取文件列表"""
        self._arch = arch
        self._version = version
        self._reset_state()
        self._log(f"正在获取 {version} 版本的文件列表...")
        self.download_btn.setEnabled(False)

        self._fetch_worker = FetchFilesWorker(version, arch)
        self._fetch_worker.success.connect(self._on_files_loaded)
        self._fetch_worker.error.connect(self._on_files_error)
        self._fetch_worker.start()

    def _reset_state(self):
        self._matches = {}
        self._all_files = []
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

        # 显示匹配文件
        self._clear_file_list()
        total = 0
        categories = {"driver": "驱动包", "container": "容器包", "vllm": "vLLM 镜像"}
        for cat, label in categories.items():
            files = matches.get(cat, [])
            total += len(files)
            for f in files:
                item = QLabel(f"  [{label}] {os.path.basename(f)}")
                item.setFont(QFont("Microsoft YaHei", 10))
                self.file_list_layout.addWidget(item)

        if total == 0:
            no_match = QLabel("未找到匹配文件。所有远程文件:")
            no_match.setStyleSheet("color: #D9534F;")
            self.file_list_layout.addWidget(no_match)
            for f in all_files[:20]:
                item = QLabel(f"  {f}")
                item.setStyleSheet("color: #888888; font-size: 10px;")
                self.file_list_layout.addWidget(item)
            self._log(f"警告: 未匹配到文件。远程共 {len(all_files)} 个文件。")
        else:
            self._log(f"找到 {total} 个匹配文件")
            self.download_btn.setEnabled(True)

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
            # 取消下载
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

        # 收集所有匹配文件
        all_matched = []
        for files in self._matches.values():
            all_matched.extend(files)

        if not all_matched:
            QMessageBox.warning(self, "无文件", "没有匹配的文件可下载")
            return

        self._download_start_time = time.time()
        self.download_btn.setText("取消下载")
        self.overall_progress.setMaximum(len(all_matched))

        self._download_worker = DownloadWorker(self._version, all_matched, save_dir)
        self._download_worker.file_progress.connect(self._on_file_progress)
        self._download_worker.overall_progress.connect(self._on_overall_progress)
        self._download_worker.file_completed.connect(self._on_file_completed)
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

            elapsed = time.time() - self._download_start_time
            if elapsed > 0 and transferred > 0:
                speed = transferred / elapsed
                self.speed_label.setText(self._format_size(speed) + "/s")

    def _on_overall_progress(self, completed: int, total: int):
        self.overall_progress.setValue(completed)
        self.overall_progress.setFormat(f"{completed}/{total}")

    def _on_file_completed(self, filename: str):
        self._log(f"✓ {filename} 下载完成")

    def _on_all_done(self):
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
```

- [ ] **Step 2: 提交**

```bash
git add downloader/ui/download_page.py
git commit -m "feat: 下载页 UI（文件列表 + 进度 + 日志）"
```

---

### Task 7: 向导主窗口

**Files:**
- Create: `downloader/ui/wizard.py`

- [ ] **Step 1: 实现向导主窗口**

```python
"""向导主窗口：QStackedWidget 管理三个页面切换"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from downloader.ui.config_page import ConfigPage
from downloader.ui.download_page import DownloadPage
from downloader.ui.welcome_page import WelcomePage


class WizardWindow(QWidget):
    """向导主窗口"""

    def __init__(self):
        super().__init__()
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
        from PyQt6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #DDDDDD; max-height: 1px;")
        main_layout.addWidget(line)

        # 页面堆栈
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        # 创建三个页面
        self.welcome_page = WelcomePage()
        self.config_page = ConfigPage()
        self.download_page = DownloadPage()

        self.stack.addWidget(self.welcome_page)
        self.stack.addWidget(self.config_page)
        self.stack.addWidget(self.download_page)

        # 连接信号
        self.welcome_page.start_clicked.connect(self._go_to_config)
        self.config_page.next_clicked.connect(self._go_to_download)
        self.config_page.back_clicked.connect(self._go_to_welcome)
        self.download_page.back_clicked.connect(self._go_to_config)

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
        steps = ["欢迎", "配置", "下载"]
        for i, name in enumerate(steps):
            # 步骤圆圈 + 文字
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

    def _go_to_config(self):
        self.stack.setCurrentIndex(1)
        self._update_steps(1)
        self.config_page.on_enter()

    def _go_to_download(self, arch: str, version: str):
        self.stack.setCurrentIndex(2)
        self._update_steps(2)
        self.download_page.on_enter(arch, version)
```

- [ ] **Step 2: 提交**

```bash
git add downloader/ui/wizard.py
git commit -m "feat: 向导主窗口（步骤指示器 + 页面切换）"
```

---

### Task 8: 应用入口

**Files:**
- Create: `downloader/main.py`

- [ ] **Step 1: 实现应用入口**

```python
"""DengLin vLLM 部署包下载工具 - 应用入口"""

import sys

from PyQt6.QtWidgets import QApplication

from downloader.ui.wizard import WizardWindow


def main():
    app = QApplication(sys.argv)

    # 全局样式
    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
        }
        QProgressBar {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            text-align: center;
            background-color: #F0F0F0;
            min-height: 20px;
        }
        QProgressBar::chunk {
            background-color: #4A90D9;
            border-radius: 3px;
        }
        QComboBox {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 4px 8px;
            background: white;
        }
        QComboBox::drop-down {
            border: none;
        }
        QPlainTextEdit {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
        }
        QLineEdit {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QScrollArea {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            background: white;
        }
    """)

    window = WizardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证应用可以启动**

```bash
cd downloader && python main.py
```

Expected: 窗口正常弹出，显示欢迎页，步骤指示器显示"欢迎"高亮

- [ ] **Step 3: 提交**

```bash
git add downloader/main.py
git commit -m "feat: 应用入口与全局样式"
```

---

### Task 9: 修复 SFTP 下载方法

**Files:**
- Modify: `downloader/sftp_client.py` 中的 `download_file` 方法

- [ ] **Step 1: 修复 paramiko SFTP 下载实现**

原 Task 2 中的 `download_file` 使用了 `getfo` 不当。修正为使用 paramiko 原生的 `get()` 方法和 `stat()` 实现断点续传检测：

```python
    def download_file(
        self,
        remote_path: str,
        local_dir: str,
        version: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """下载单个文件，支持断点续传检测"""
        remote_full = f"{REMOTE_BASE_DIR}/{version}/{remote_path}"
        local_path = os.path.join(local_dir, os.path.basename(remote_path))

        # 获取远程文件大小
        remote_stat = self._sftp.stat(remote_full)
        total_size = remote_stat.st_size

        # 断点续传检查
        if os.path.exists(local_path):
            local_size = os.path.getsize(local_path)
            if local_size == total_size:
                if progress_callback:
                    progress_callback(total_size, total_size)
                return local_path

        # 使用 paramiko get 方法下载，支持进度回调
        self._sftp.get(remote_full, local_path, callback=progress_callback)
        return local_path
```

- [ ] **Step 2: 提交**

```bash
git add downloader/sftp_client.py
git commit -m "fix: 修正 SFTP 下载方法，使用 paramiko 原生 get()"
```
