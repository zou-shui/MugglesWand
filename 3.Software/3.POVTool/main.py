# -*- coding: utf-8 -*-
"""MugglesWand POV 图案生成器入口。

用法：python main.py   （在 POVTool/ 目录下）
"""

import sys

from PySide6.QtWidgets import QApplication

from gui import MainWindow, QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MugglesWand POV 图案生成器")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
