# Offline inspection dialog (Matplotlib).
# Shown after disconnect — lets the user browse the full recording
# by channel and signal mode. Does not update live.

import numpy as np
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from models.signal_processor import process_signal


class OfflineInspectionDialog(QDialog):
    """Matplotlib dialog for post-recording signal inspection."""

    MODES = ["original", "filtered", "rms"]

    def __init__(
        self,
        x_full: np.ndarray,
        data: np.ndarray,
        sampling_rate: float = 2000.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Offline Signal Inspection")
        self.resize(1100, 650)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self._x = x_full
        self._data = data
        self._n_channels = data.shape[0]
        self._sampling_rate = sampling_rate

        self._build_ui()
        self._replot()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # controls row
        ctrl = QHBoxLayout()

        ctrl.addWidget(QLabel("Channel:"))
        self._channel_spin = QSpinBox()
        self._channel_spin.setRange(1, self._n_channels)
        self._channel_spin.setValue(1)
        self._channel_spin.setSuffix(f" / {self._n_channels}")
        self._channel_spin.valueChanged.connect(self._replot)
        ctrl.addWidget(self._channel_spin)

        ctrl.addSpacing(20)
        ctrl.addWidget(QLabel("Signal mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Original", "Filtered", "RMS"])
        self._mode_combo.currentIndexChanged.connect(self._replot)
        ctrl.addWidget(self._mode_combo)

        ctrl.addStretch()
        self._info_label = QLabel("")
        ctrl.addWidget(self._info_label)
        root.addLayout(ctrl)

        # matplotlib canvas
        self._fig = Figure(figsize=(10, 5), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        self._toolbar = NavigationToolbar(self._canvas, self)

        root.addWidget(self._toolbar)
        root.addWidget(self._canvas, stretch=1)

        # close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _replot(self) -> None:
        """Redraw for the selected channel and mode."""
        ch = self._channel_spin.value() - 1
        mode = self.MODES[self._mode_combo.currentIndex()]

        raw_2d = self._data[ch : ch + 1, :]
        processed = process_signal(raw_2d, self._sampling_rate, mode)
        y = processed[0, :]

        self._ax.clear()
        self._ax.plot(self._x, y, linewidth=0.8, color="#1e6fba")
        self._ax.set_xlabel("Time (s)")
        self._ax.set_ylabel("Amplitude")
        self._ax.set_title(f"Channel {ch + 1} — {mode.upper()} signal")
        self._ax.grid(True, alpha=0.3)

        duration = self._x[-1] if len(self._x) > 0 else 0.0
        self._info_label.setText(f"Duration: {duration:.1f} s  |  Samples: {len(self._x)}")
        self._canvas.draw()
