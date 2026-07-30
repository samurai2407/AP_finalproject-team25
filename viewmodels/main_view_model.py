# ViewModel: QTimer polling loop, signal processing dispatch, Qt signal emission.
# Sits between the TCP model and the PySide6 views — no widgets imported here.

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from models.tcp_client_model import TcpClientModel
from models.signal_processor import process_signal


class MainViewModel(QObject):
    """QObject that owns the update timer, application state, and Qt signals.

    Polls the TCP model on every timer tick, applies signal processing,
    and emits results to the View. No widgets are imported or created here.
    """
    # emitted each timer tick with processed (x, y) for the active channel
    plot_updated = Signal(object, object)

    # emitted each timer tick with (x, data) for all-channels view
    all_channels_updated = Signal(object, object)

    # status text for the status bar
    status_updated = Signal(str)

    # emitted once on disconnect with the full recording (x, data)
    recording_ready = Signal(object, object)

    TIMER_INTERVAL_MS: int = 20   # ~50 fps
    SAMPLING_RATE: int = 2000
    CHANNELS: int = 32

    def __init__(self) -> None:
        """Set up the TCP model, state variables, and the QTimer polling loop."""
        super().__init__()

        self.model = TcpClientModel(
            host="localhost",
            port=12345,
            sampling_rate=self.SAMPLING_RATE,
            channels=self.CHANNELS,
            samples_per_packet=18,
            window_seconds=10.0,
        )

        self.selected_channel: int = 0
        self.signal_mode: str = "original"   # "original" | "filtered" | "rms"
        self.show_all_channels: bool = False
        self.is_streaming: bool = False

        self._timer = QTimer(self)
        self._timer.setInterval(self.TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timer)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, port: int) -> None:
        """Connect to the TCP server and start the update timer."""
        if self.is_streaming:
            return
        try:
            self.model.port = port
            self.model.reset_buffers()
            self.model.connect()
            self.is_streaming = True
            self._timer.start()
            self.status_updated.emit(f"Connected to localhost:{port} — streaming started.")
        except OSError as exc:
            self.status_updated.emit(f"Could not connect: {exc}")

    def disconnect(self) -> None:
        """Stop the timer, close the socket, and make the recording available."""
        if not self.is_streaming and not self.model.is_connected:
            return
        self._timer.stop()
        self.is_streaming = False
        self.model.disconnect()
        self.status_updated.emit("Disconnected.")
        self._emit_recording_ready()

    # ------------------------------------------------------------------
    # State setters (called from the View)
    # ------------------------------------------------------------------

    def set_channel(self, channel: int) -> None:
        """Set the active channel index (0-based)."""
        if 0 <= channel < self.CHANNELS:
            self.selected_channel = channel

    def set_signal_mode(self, mode: str) -> None:
        """Switch between 'original', 'filtered', and 'rms'."""
        if mode in ("original", "filtered", "rms"):
            self.signal_mode = mode

    def set_show_all_channels(self, show: bool) -> None:
        """Toggle all-channels overview on or off."""
        self.show_all_channels = show

    # ------------------------------------------------------------------
    # Timer callback
    # ------------------------------------------------------------------

    def _on_timer(self) -> None:
        """Poll the socket and push new data to the view."""
        self.model.receive_data()

        # Handle server-side disconnect
        if not self.model.is_connected and self.is_streaming:
            self._timer.stop()
            self.is_streaming = False
            self.status_updated.emit("Connection closed by server.")
            self._emit_recording_ready()
            return

        if not self.model.has_data():
            return

        if self.show_all_channels:
            self._emit_all_channels()
        else:
            self._emit_single_channel()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _emit_single_channel(self) -> None:
        """Process and emit (x, y) for the currently selected channel."""
        x, raw = self.model.get_window(self.selected_channel)
        raw_2d = raw[np.newaxis, :]   # process_signal expects (channels, samples)
        processed = process_signal(raw_2d, self.SAMPLING_RATE, self.signal_mode)
        self.plot_updated.emit(x, processed[0, :])

    def _emit_all_channels(self) -> None:
        """Process and emit (x, data) for all 32 channels."""
        x, raw = self.model.get_all_channels_window()
        processed = process_signal(raw, self.SAMPLING_RATE, self.signal_mode)
        self.all_channels_updated.emit(x, processed)

    def _emit_recording_ready(self) -> None:
        """Emit the full recorded buffer for offline inspection, or a warning if empty."""
        rec = self.model.recorded_buffer
        if rec.shape[1] < 2:
            self.status_updated.emit(
                "Disconnected. No data was recorded for offline inspection."
            )
            return
        n = rec.shape[1]
        x = np.arange(n) / self.SAMPLING_RATE
        self.recording_ready.emit(x, rec)
        self.status_updated.emit(
            f"Disconnected. {n} samples ({n / self.SAMPLING_RATE:.1f} s) recorded. "
            "Offline plot is available."
        )
