"""SFTP 凭据持久化存储（基于 QSettings）"""

from __future__ import annotations

from PyQt6.QtCore import QSettings


_SETTINGS_KEY_USER = "sftp/username"
_SETTINGS_KEY_PASS = "sftp/password"


def save_credentials(username: str, password: str):
    """保存凭据到 QSettings"""
    settings = QSettings("DengLin", "vLLMDownloader")
    settings.setValue(_SETTINGS_KEY_USER, username)
    settings.setValue(_SETTINGS_KEY_PASS, password)


def load_credentials() -> tuple[str, str] | None:
    """加载已保存的凭据，返回 (username, password) 或 None"""
    settings = QSettings("DengLin", "vLLMDownloader")
    user = settings.value(_SETTINGS_KEY_USER, "")
    passwd = settings.value(_SETTINGS_KEY_PASS, "")
    if user:
        return (user, passwd)
    return None


def clear_credentials():
    """清除已保存的凭据"""
    settings = QSettings("DengLin", "vLLMDownloader")
    settings.remove(_SETTINGS_KEY_USER)
    settings.remove(_SETTINGS_KEY_PASS)
