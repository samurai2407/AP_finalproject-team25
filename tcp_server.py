"""
TCP Server — replays recording.pkl at the correct sample rate.
=============================================================
This is the server provided alongside Exercise 5.
It loads the EMG recording, then streams it to any connecting client
18 samples at a time at 2000 Hz (one packet every 9 ms).

Usage: 
    python tcp_server.py [port]          default port: 12345

The server loops the recording continuously so the client always has data.
"""

import socket
import sys
import time
import pathlib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT: int = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
HOST: str = "localhost"
CHANNELS: int = 32
SAMPLES_PER_PACKET: int = 18
DTYPE = np.float64
SAMPLING_RATE: int = 2000
PACKET_INTERVAL: float = SAMPLES_PER_PACKET / SAMPLING_RATE   # 0.009 s

# ---------------------------------------------------------------------------
# Load recording
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).parent
PKL_PATH = REPO_ROOT / "recording.pkl"

print(f"Loading recording from {PKL_PATH} ...")
data = pd.read_pickle(PKL_PATH)
emg: np.ndarray = data["biosignal"]          # shape: (channels, window, n_windows)

# Flatten to (channels, total_samples)
n_ch, win_size, n_wins = emg.shape
flat: np.ndarray = emg.transpose(2, 1, 0).reshape(-1, n_ch).T.astype(DTYPE)

# The protocol sends exactly CHANNELS channels.
# The recording may have more (e.g. 38); use the first 32.
if flat.shape[0] > CHANNELS:
    flat = flat[:CHANNELS, :]
elif flat.shape[0] < CHANNELS:
    # Pad with zeros if somehow fewer channels exist.
    pad = np.zeros((CHANNELS - flat.shape[0], flat.shape[1]), dtype=DTYPE)
    flat = np.vstack([flat, pad])

# Trim to an exact multiple of SAMPLES_PER_PACKET
total = (flat.shape[1] // SAMPLES_PER_PACKET) * SAMPLES_PER_PACKET
flat = flat[:, :total]

print(f"Signal shape after flatten: {flat.shape}  "
      f"({flat.shape[1] / SAMPLING_RATE:.1f} s)")
print(f"Server will stream on {HOST}:{PORT}")

# ---------------------------------------------------------------------------
# Server loop
# ---------------------------------------------------------------------------
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((HOST, PORT))
server_sock.listen(1)

print(f"Waiting for client connection on port {PORT} ...")

while True:
    client_sock, addr = server_sock.accept()
    print(f"Client connected: {addr}")

    n_packets = flat.shape[1] // SAMPLES_PER_PACKET
    pkt_idx = 0

    try:
        while True:
            t_start = time.perf_counter()

            chunk = flat[:, pkt_idx * SAMPLES_PER_PACKET:(pkt_idx + 1) * SAMPLES_PER_PACKET]
            client_sock.sendall(chunk.tobytes())

            pkt_idx = (pkt_idx + 1) % n_packets

            # Sleep for the remainder of the packet interval to hit ~2000 Hz.
            elapsed = time.perf_counter() - t_start
            sleep_for = PACKET_INTERVAL - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    except (BrokenPipeError, ConnectionResetError, OSError):
        print(f"Client {addr} disconnected.")
    finally:
        client_sock.close()

    print("Waiting for next client ...")
