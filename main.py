# Entry point — start the TCP server from Exercise 5 before running this.
# Usage: python main.py

import sys
import matplotlib
matplotlib.use("QtAgg")  # set backend before any other matplotlib import

from PySide6.QtWidgets import QApplication

from viewmodels.main_view_model import MainViewModel
from views.main_view import MainView


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("EMG Live Viewer")
    app.setApplicationVersion("1.0.0")

    view_model = MainViewModel()
    view = MainView(view_model)
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
