"""DengLin vLLM 部署包下载工具 - 应用入口"""

import sys

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from downloader.ui.wizard import WizardWindow


def main():
    app = QApplication(sys.argv)

    # QSettings 组织/应用名称（凭据持久化需要）
    QCoreApplication.setOrganizationName("DengLin")
    QCoreApplication.setApplicationName("vLLMDownloader")

    # 全局样式
    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "PingFang SC", Helvetica, sans-serif;
        }
        QProgressBar {
            border: 1px solid #D8DEE8;
            border-radius: 8px;
            text-align: center;
            background: #F8FAFC;
            min-height: 22px;
        }
        QProgressBar::chunk {
            background: #2563EB;
            border-radius: 7px;
        }
        QCheckBox {
            spacing: 8px;
            color: #111827;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
    """)

    window = WizardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
