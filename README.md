# EMG Live Viewer — Final Project

## Group Information

**Group:** Group 25

| Name | Email | Responsibility |
|------|-------|---------------|
| Prem Mahajan | prem.mahajan@fau.de | TCP client model, signal processor, ViewModel |
| Nishant Gangwar | nishant.gangwar@fau.de | VisPy live plot views, all-channels overview |
| Husam Altamimi | husam.m.altamimi@fau.de | Offline Matplotlib inspection, main view, README |

---

## Overview

A **PySide6 desktop application** that connects to a TCP server, visualises
32-channel EMG data in real time using **VisPy**, and lets the user inspect
the full recording offline with **Matplotlib** after disconnecting.

The project follows the **MVVM** (Model – View – ViewModel) architecture pattern.

---

## Project Structure

```
final_project/
├── main.py                   Entry point
├── tcp_server.py             TCP server from Exercise 5 (included for graders)
├── recording.pkl             EMG recording data (tracked in Git, included in clone)
├── requirements.txt          Python dependencies
├── README.md                 This file
├── models/
│   ├── tcp_client_model.py   TCP socket, byte buffer, rolling data buffer
│   └── signal_processor.py   Bandpass filter, RMS envelope, mode dispatch
├── viewmodels/
│   └── main_view_model.py    QTimer polling loop, Qt signals, application state
└── views/
    ├── main_view.py          Main QMainWindow and control panel
    ├── plot_view.py          VisPy single-channel and all-channels widgets
    └── offline_view.py       Matplotlib QDialog for offline inspection
```

### MVVM Architecture

| Layer     | File(s) | Responsibility |
|-----------|---------|----------------|
| Model     | `tcp_client_model.py` | TCP I/O, raw byte buffering, rolling data buffer. No GUI imports. |
| Model     | `signal_processor.py` | Stateless signal processing functions. No GUI imports. |
| ViewModel | `main_view_model.py`  | Owns the QTimer, application state, and Qt signals. No widgets. |
| View      | `main_view.py`, `plot_view.py`, `offline_view.py` | All widgets and plots. No TCP or signal math. |

The View never touches the TCP socket directly. The Model never imports any Qt
widget. All communication between layers flows through Qt signals and slots.

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/samurai2407/AP_finalproject-team25.git
cd AP_finalproject-team25
pip install -r requirements.txt
```

`recording.pkl`, `tcp_server.py`, and all source files are tracked in Git and
will be present immediately after cloning. No manual file copying is required.

---

## Running the Application

### Step 1 — Start the TCP server

Open a terminal in the project root and run:

```bash
python tcp_server.py
```

The server loads `recording.pkl` from the same directory, then listens on
`localhost:12345` by default. You should see:

```
Loading recording from .../recording.pkl ...
Signal shape after flatten: (32, XXXXX)  (XX.X s)
Server will stream on localhost:12345
Waiting for client connection on port 12345 ...
```

> The server must be running **before** you launch the GUI.

### Step 2 — Start the GUI

Open a second terminal in the same directory:

```bash
python main.py
```

---

## How to Use

### Connecting

1. Enter the server **port** in the "Port" field (default `12345`).
2. Click **Connect**.
3. The status bar at the bottom and the coloured **● indicator** in the dock
   will both confirm a successful connection. Streaming starts immediately.

### Live Plot — Single Channel

- Use the **Channel** spinner to choose which of the 32 channels to display.
- The rolling window shows the last **10 seconds** of data.
- The **x-axis** shows elapsed time in seconds.
- The **y-axis** scales dynamically to the current signal amplitude — the
  signal is never clipped or out of range.

### Live Plot — All Channels

- Click **Plot All Channels** to switch to the stacked overview.
- All 32 channels are drawn simultaneously. Each channel is normalised and
  shifted by a fixed vertical offset so all signals remain readable without
  overlap.
- Click **Single Channel View** to return to the single-channel plot.

### Signal Modes

Use the **Signal Mode** dropdown to switch between three processing modes.
The selected mode applies to both the live VisPy plot and the offline
Matplotlib plot.

| Mode | Description |
|------|-------------|
| **Original** | Raw samples, no processing applied |
| **Filtered** | Zero-phase Butterworth bandpass filter (see parameters below) |
| **RMS** | Rolling RMS envelope computed on the filtered signal |

### Offline Inspection

1. Click **Disconnect** to stop streaming.
2. The Matplotlib offline inspection window **opens automatically**.
3. Inside the dialog:
   - Use the **Channel** spinner to select a channel (1 – 32).
   - Use the **Signal mode** dropdown to switch between Original, Filtered, and RMS.
   - Use the Matplotlib toolbar to zoom, pan, and save the plot.
4. You can also re-open the dialog at any time by clicking
   **Open Offline Plot (Matplotlib)** in the left dock.

---

## Signal Processing Parameters

### Bandpass Filter

| Parameter   | Value | Rationale |
|-------------|-------|-----------|
| Filter type | Butterworth | Maximally flat passband, no ripple |
| Order       | 4 | Good roll-off, minimal phase distortion |
| Low cutoff  | 20 Hz | Removes DC offset and movement artefacts |
| High cutoff | 450 Hz | Well below Nyquist (1000 Hz) at 2000 Hz sampling rate |
| Method      | Zero-phase `filtfilt` | No time delay introduced in the output |

### RMS Envelope

| Parameter   | Value | Rationale |
|-------------|-------|-----------|
| Window size | 200 samples (100 ms at 2000 Hz) | Standard EMG envelope extraction length |
| Method      | `scipy.ndimage.uniform_filter1d` on `data²`, then `sqrt` | Vectorised rolling mean, preserves full array shape |
| Input       | Filtered signal | RMS is always applied after bandpass filtering |

---

## Error Handling

The application handles all common failure cases without crashing. Errors are
shown as plain text in the status bar at the bottom of the window.

| Situation | Behaviour |
|-----------|-----------|
| Server not running | `OSError` caught; message shown in status bar |
| Wrong port entered | Invalid input caught before connecting; message shown |
| Connection lost mid-stream | Timer stops automatically; offline plot offered |
| Disconnect before any data | Clear status message; offline button stays disabled |
| Invalid channel or mode value | Validated in ViewModel before reaching the model |

---

## Dependencies

```
numpy>=1.26,<3
scipy>=1.12,<2
PySide6>=6.7,<7
vispy>=0.14,<1
matplotlib>=3.8,<4
pandas>=2.0,<3
```
