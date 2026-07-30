# Main window: control dock (left) + VisPy plot area (centre).
# Wires user actions to the ViewModel; never touches TCP or signal math.

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from views.plot_view import AllChannelsPlotWidget, SingleChannelPlotWidget
from views.offline_view import OfflineInspectionDialog


class MainView(QMainWindow):
    """Top-level application window."""

    N_CHANNELS: int = 32

    def __init__(self, view_model) -> None:
        """Initialise the window, build all widgets, and wire signals."""
        super().__init__()
        self._vm = view_model
        self._recording_x: np.ndarray | None = None
        self._recording_data: np.ndarray | None = None

        self.setWindowTitle("EMG Live Viewer")
        self.resize(1300, 800)

        self._build_central_widget()
        self._build_control_dock()
        self._build_status_bar()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_central_widget(self) -> None:
        """Stacked widget: index 0 = single channel, index 1 = all channels."""
        self._plot_stack = QStackedWidget()
        self._single_plot = SingleChannelPlotWidget()
        self._all_plot = AllChannelsPlotWidget(n_channels=self.N_CHANNELS)
        self._plot_stack.addWidget(self._single_plot)
        self._plot_stack.addWidget(self._all_plot)
        self.setCentralWidget(self._plot_stack)

    def _build_control_dock(self) -> None:
        """Left dock: connection controls, channel picker, mode selector."""
        dock_content = QWidget()
        dock_layout = QVBoxLayout(dock_content)
        dock_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        dock_layout.setSpacing(12)

        # TCP connection
        conn_group = QGroupBox("TCP Connection")
        conn_form = QFormLayout(conn_group)

        self._port_edit = QLineEdit("12345")
        self._port_edit.setPlaceholderText("e.g. 12345")
        conn_form.addRow("Port:", self._port_edit)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setStyleSheet(
            "QPushButton { background:#2a7d4f; color:white; font-weight:bold; "
            "padding:6px; border-radius:4px; }"
            "QPushButton:hover { background:#35a265; }"
        )
        conn_form.addRow(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.setStyleSheet(
            "QPushButton { background:#a03030; color:white; font-weight:bold; "
            "padding:6px; border-radius:4px; }"
            "QPushButton:hover { background:#c04040; }"
            "QPushButton:disabled { background:#888; }"
        )
        conn_form.addRow(self._disconnect_btn)

        self._conn_status_label = QLabel("● Disconnected")
        self._conn_status_label.setStyleSheet("color: #a03030; font-weight: bold;")
        conn_form.addRow("Status:", self._conn_status_label)

        dock_layout.addWidget(conn_group)

        # Channel selection
        ch_group = QGroupBox("Channel")
        ch_form = QFormLayout(ch_group)

        self._channel_spin = QSpinBox()
        self._channel_spin.setRange(1, self.N_CHANNELS)
        self._channel_spin.setValue(1)
        self._channel_spin.setSuffix(f" / {self.N_CHANNELS}")
        ch_form.addRow("Channel:", self._channel_spin)

        self._all_channels_btn = QPushButton("Plot All Channels")
        self._all_channels_btn.setCheckable(True)
        ch_form.addRow(self._all_channels_btn)

        dock_layout.addWidget(ch_group)

        # Signal mode
        mode_group = QGroupBox("Signal Mode")
        mode_form = QFormLayout(mode_group)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Original", "Filtered", "RMS"])
        mode_form.addRow("Mode:", self._mode_combo)

        dock_layout.addWidget(mode_group)

        # Offline inspection
        offline_group = QGroupBox("Offline Inspection")
        offline_layout = QVBoxLayout(offline_group)
        self._offline_btn = QPushButton("Open Offline Plot (Matplotlib)")
        self._offline_btn.setEnabled(False)
        offline_layout.addWidget(self._offline_btn)
        dock_layout.addWidget(offline_group)

        dock_layout.addStretch()

        dock = QDockWidget("Controls", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        dock.setWidget(dock_content)
        dock.setMinimumWidth(220)
        dock.setMaximumWidth(300)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def _build_status_bar(self) -> None:
        """Create the bottom status bar with an initial ready message."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready. Enter a port and press Connect.")

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connect all View↔ViewModel signals and slots."""
        # view → viewmodel
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        self._disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self._channel_spin.valueChanged.connect(self._on_channel_changed)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._all_channels_btn.toggled.connect(self._on_all_channels_toggled)
        self._offline_btn.clicked.connect(self._open_offline_dialog)

        # viewmodel → view
        self._vm.plot_updated.connect(self._single_plot.update_plot)
        self._vm.all_channels_updated.connect(self._all_plot.update_plot)
        self._vm.status_updated.connect(self._on_status_updated)
        self._vm.recording_ready.connect(self._on_recording_ready)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_connect_clicked(self) -> None:
        """Validate the port field and tell the ViewModel to connect."""
        port_text = self._port_edit.text().strip()
        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self._status_bar.showMessage(
                "Invalid port number. Please enter a value between 1 and 65535."
            )
            return

        self._vm.connect(port)
        if self._vm.is_streaming:
            self._set_connected_ui(True)

    def _on_disconnect_clicked(self) -> None:
        """Stop streaming and reset the UI to the disconnected state."""
        self._vm.disconnect()
        self._set_connected_ui(False)

    def _on_channel_changed(self, value: int) -> None:
        """Forward the selected channel to the ViewModel (converts 1-based to 0-based)."""
        self._vm.set_channel(value - 1)

    def _on_mode_changed(self, index: int) -> None:
        """Map the combo-box index to a mode string and update the ViewModel."""
        modes = ["original", "filtered", "rms"]
        self._vm.set_signal_mode(modes[index])

    def _on_all_channels_toggled(self, checked: bool) -> None:
        """Switch the plot stack between single-channel and all-channels views."""
        self._vm.set_show_all_channels(checked)
        if checked:
            self._plot_stack.setCurrentIndex(1)
            self._all_channels_btn.setText("Single Channel View")
        else:
            self._plot_stack.setCurrentIndex(0)
            self._all_channels_btn.setText("Plot All Channels")

    def _on_status_updated(self, message: str) -> None:
        """Update the status bar and the coloured connection indicator label."""
        self._status_bar.showMessage(message)
        if "Connected" in message and "Could not" not in message:
            self._conn_status_label.setText("● Connected")
            self._conn_status_label.setStyleSheet("color: #2a7d4f; font-weight: bold;")
        elif "Disconnected" in message or "closed" in message:
            self._conn_status_label.setText("● Disconnected")
            self._conn_status_label.setStyleSheet("color: #a03030; font-weight: bold;")
            self._set_connected_ui(False)

    def _on_recording_ready(self, x: np.ndarray, data: np.ndarray) -> None:
        """Cache the recording and automatically open the offline inspection dialog."""
        self._recording_x = x
        self._recording_data = data
        self._offline_btn.setEnabled(True)
        # Auto-open the offline plot as soon as the recording is available
        self._open_offline_dialog()

    def _open_offline_dialog(self) -> None:
        """Open the Matplotlib offline inspection dialog for the recorded data."""
        if self._recording_x is None or self._recording_data is None:
            self._status_bar.showMessage(
                "No recorded data available yet. Connect and stream first."
            )
            return
        try:
            dlg = OfflineInspectionDialog(
                x_full=self._recording_x,
                data=self._recording_data,
                sampling_rate=self._vm.SAMPLING_RATE,
                parent=self,
            )
            dlg.show()
        except Exception as exc:
            self._status_bar.showMessage(f"Could not open offline plot: {exc}")

    # ------------------------------------------------------------------

    def _set_connected_ui(self, connected: bool) -> None:
        """Enable/disable controls based on connection state."""
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._port_edit.setEnabled(not connected)
