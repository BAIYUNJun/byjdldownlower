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
