"""Render representative branded UI states for visual QA."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from downloader.ui.wizard import WizardWindow


OUT_DIR = Path("/private/tmp/byjdldown_branded_ui")


def render() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    QCoreApplication.setOrganizationName("DengLin")
    QCoreApplication.setApplicationName("vLLMDownloader")

    window = WizardWindow()
    window.resize(940, 640)
    window.show()
    app.processEvents()
    window.grab().save(str(OUT_DIR / "01_connection.png"))

    window.stack.setCurrentIndex(1)
    window._update_steps(1)
    config = window.config_page
    config._release_container.setVisible(True)
    config._release_type = "standard"
    config._release_segment.set_checked("standard")
    config._arch_container.setVisible(True)
    config._os_container.setVisible(True)
    config.x86_btn.setChecked(True)
    if "linux" in config._os_btns:
        config._os_btns["linux"].setChecked(True)
    config.version_combo.clear()
    config.version_combo.addItems([
        "V2-General_release-20260430",
        "V2-General_release-20260420",
    ])
    config.version_combo.setCurrentIndex(0)
    config.version_combo.setEnabled(True)
    config.version_status.setText("找到 2 个版本（最新: V2-General_release-20260430）")
    config.next_btn.setEnabled(True)
    app.processEvents()
    window.grab().save(str(OUT_DIR / "02_config_standard.png"))

    window.stack.setCurrentIndex(2)
    window._selected_arch = "x86"
    window._selected_os = "linux"
    window._selected_version = "V2-General_release-20260430"
    window._release_type = "standard"
    window._update_steps(2)
    mode = window.mode_page
    mode._arch = "x86"
    mode._version = "V2-General_release-20260430"
    mode._os = "linux"
    mode._release_type = "standard"
    mode.header.set_text("选择下载内容", "选择预设或手动勾选标准发布组件")
    mode.info_label.setText("当前: x86_64 | Linux | V2-General_release-20260430")
    mode._setup_standard_mode("linux")
    first_preset = next(iter(mode._preset_btns))
    mode._preset_btns[first_preset].setChecked(True)
    mode._on_preset_clicked(first_preset)
    app.processEvents()
    window.grab().save(str(OUT_DIR / "03_content_selection.png"))

    window.stack.setCurrentIndex(3)
    window._update_steps(3)
    download = window.download_page
    download._category_labels = {
        "driver": "驱动包",
        "container": "容器包",
        "sdk": "SDK",
    }
    download._reset_state()
    download._on_files_loaded(
        {
            "driver": [
                "Base_driver/dlinfer-driver-manylinux-super-long-x86_64-release-package.tar.gz"
            ],
            "container": ["Docker/container-x86-linux.tar.gz"],
            "sdk": ["SDK/dl-sdk-linux-x86_64.tar.gz"],
        },
        [],
    )
    download.dir_edit.setText("/Users/baiyunjun/Downloads")
    download.overall_progress.setMaximum(3)
    download.overall_progress.setValue(1)
    download.overall_progress.setFormat("1/3")
    download._current_file_start_time -= 1
    download._on_file_progress(
        "dlinfer-driver-manylinux-super-long-x86_64-release-package.tar.gz",
        42,
        100,
    )
    download.speed_label.setText("12.5 MB/s")
    download._log("正在下载示例文件...")
    app.processEvents()
    window.grab().save(str(OUT_DIR / "04_download_task.png"))

    print(OUT_DIR)


if __name__ == "__main__":
    render()
