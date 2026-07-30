# TCP client: socket connection, byte-stream buffering, packet extraction,
# rolling data buffer. All network I/O lives here — no GUI code.
#
# Protocol:  32 channels x 18 samples x float64 = 4608 bytes per packet

import socket
import numpy as np


class TcpClientModel:
    """Receives EMG data from a TCP server and keeps a rolling buffer."""

    CHANNELS: int = 32
    SAMPLES_PER_PACKET: int = 18
    DTYPE = np.float64

    def __init__(
        self,
        host: str = "localhost",
        port: int = 12345,
        sampling_rate: int = 2000,
        channels: int = 32,
        samples_per_packet: int = 18,
        window_seconds: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.channels = channels
        self.samples_per_packet = samples_per_packet
        self.window_seconds = window_seconds

        self.packet_size: int = self.channels * self.samples_per_packet
        self.packet_size_bytes: int = self.packet_size * np.dtype(self.DTYPE).itemsize

        self.window_size: int = int(self.sampling_rate * self.window_seconds)

        self._socket: socket.socket | None = None
        self.is_connected: bool = False

        # TCP is a stream — accumulate raw bytes until a full packet arrives
        self._byte_buffer: bytearray = bytearray()

        # Rolling window buffer, shape (channels, samples)
        self.data_buffer: np.ndarray = np.empty((self.channels, 0), dtype=self.DTYPE)

        # Full recording, never trimmed — used for offline inspection
        self.recorded_buffer: np.ndarray = np.empty((self.channels, 0), dtype=self.DTYPE)

        self.total_samples_received: int = 0

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open a non-blocking TCP connection to the server."""
        if self.is_connected:
            return
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))
        # Non-blocking so recv() raises BlockingIOError instead of freezing Qt
        self._socket.setblocking(False)
        self.is_connected = True

    def disconnect(self) -> None:
        """Close the socket and mark as disconnected."""
        self.is_connected = False
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def reset_buffers(self) -> None:
        """Clear all buffers before starting a fresh recording."""
        self._byte_buffer = bytearray()
        self.data_buffer = np.empty((self.channels, 0), dtype=self.DTYPE)
        self.recorded_buffer = np.empty((self.channels, 0), dtype=self.DTYPE)
        self.total_samples_received = 0

    # ------------------------------------------------------------------
    # Data reception
    # ------------------------------------------------------------------

    def receive_data(self) -> None:
        """
        Drain all bytes available on the socket (called by the ViewModel timer).

        BlockingIOError is the normal exit — it means no more data right now.
        """
        if not self.is_connected or self._socket is None:
            return

        while True:
            try:
                new_bytes = self._socket.recv(4096)
                if not new_bytes:
                    # Server closed the connection cleanly
                    self.disconnect()
                    return
                self._byte_buffer.extend(new_bytes)
            except BlockingIOError:
                break
            except OSError:
                self.disconnect()
                return

        self._extract_packets_from_buffer()

    def _extract_packets_from_buffer(self) -> None:
        """Pull complete 4608-byte packets out of the byte buffer."""
        packets: list[np.ndarray] = []

        while len(self._byte_buffer) >= self.packet_size_bytes:
            raw = bytes(self._byte_buffer[: self.packet_size_bytes])
            del self._byte_buffer[: self.packet_size_bytes]
            packet = np.frombuffer(raw, dtype=self.DTYPE).reshape(
                self.channels, self.samples_per_packet
            )
            packets.append(packet)

        if not packets:
            return

        new_data: np.ndarray = np.concatenate(packets, axis=1)
        self.total_samples_received += new_data.shape[1]

        # Append to full recording
        self.recorded_buffer = np.concatenate((self.recorded_buffer, new_data), axis=1)

        # Append to rolling window and drop old samples
        self.data_buffer = np.concatenate((self.data_buffer, new_data), axis=1)
        if self.data_buffer.shape[1] > self.window_size:
            self.data_buffer = self.data_buffer[:, -self.window_size :]

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def has_data(self) -> bool:
        """True when at least 2 samples are buffered."""
        return self.data_buffer.shape[1] >= 2

    def get_window(self, channel: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (time_axis, signal) for a single channel's rolling window."""
        y = self.data_buffer[channel, :]
        x = np.arange(y.shape[0]) / self.sampling_rate
        return x, y

    def get_all_channels_window(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (time_axis, data) for all channels. data shape: (channels, samples)."""
        data = self.data_buffer
        x = np.arange(data.shape[1]) / self.sampling_rate
        return x, data

    def get_signal_time_seconds(self) -> float:
        """Total seconds of data received since last connect."""
        return self.total_samples_received / self.sampling_rate
