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
                    try:
                        self._sftp.stat(f"{target}/{entry}")
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
        """下载单个文件，支持断点续传检测"""
        remote_full = f"{REMOTE_BASE_DIR}/{version}/{remote_path}"
        local_path = os.path.join(local_dir, os.path.basename(remote_path))

        remote_stat = self._sftp.stat(remote_full)
        total_size = remote_stat.st_size

        # 断点续传检查
        if os.path.exists(local_path):
            local_size = os.path.getsize(local_path)
            if local_size == total_size:
                if progress_callback:
                    progress_callback(total_size, total_size)
                return local_path

        self._sftp.get(remote_full, local_path, callback=progress_callback)
        return local_path

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
