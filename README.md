# EMG Live Viewer — Final Project

## Group information

| Name | Responsibility |
|------|---------------|
| Prem Mahajan (prem.mahajan@fau.de) | TCP client model, signal processor, ViewModel |
| Nishant Gangwar () | VisPy live plot views, all-channels overview |
| Husam Altamimi () | Offline Matplotlib inspection, main view, README |

---

## Overview

A **PySide6 desktop application** that connects to the Exercise 5 TCP server,
visualises 32-channel EMG data in real time using **VisPy**, and lets the user
inspect the full recording offline with **Matplotlib** after disconnecting.

The application follows the **MVVM** (Model – View – ViewModel) pattern.

---

## Project structure

```
final_project/
├── main.py                        Entry point
├── tcp_server.py                  TCP server (Exercise 5, included for graders)
├── requirements.txt               Dependency list
├── README.md                      This file
├── models/
│   ├── tcp_client_model.py        TCP socket, byte buffer, rolling buffer
│   └── signal_processor.py        Bandpass filter, RMS, mode dispatch
├── viewmodels/
│   └── main_view_model.py         QTimer-driven update loop, Qt signals
└── views/
    ├── main_view.py               Main QMainWindow, control panel
    ├── plot_view.py               VisPy single-channel + all-channels widgets
    └── offline_view.py            Matplotlib QDialog for offline inspection
```

### MVVM responsibilities

| Layer      | File(s)                        | Responsibility |
|------------|-------------------------------|----------------|
| Model      | `tcp_client_model.py`          | TCP I/O, byte buffer, rolling data buffer |
| Model      | `signal_processor.py`          | Stateless signal processing (no GUI) |
| ViewModel  | `main_view_model.py`           | QTimer loop, state, Qt signals — no widgets |
| View       | `main_view.py`, `plot_view.py`, `offline_view.py` | Widgets, plots — no TCP or math |

---

## Installation

### Using pip

```bash
cd final_project
pip install -r requirements.txt
```

### Using uv (recommended — matches the course setup)

```bash
cd final_project
uv pip install -r requirements.txt
```

---

## Running the application

### 1. Start the TCP server

`tcp_server.py` (from Exercise 5) has been included in the root of this
repository for convenience.  Start it in a separate terminal **before**
launching the GUI:

```bash
python tcp_server.py
```

The server listens on `localhost:12345` by default.

### 2. Start the GUI

```bash
python main.py
```

---

## How to use

### Connect to the TCP server

1. Enter the server **port** in the "Port" field (default `12345`).
2. Click **Connect**.
3. The status bar and the connection indicator will confirm a successful
   connection.  Streaming starts immediately.

### Live plot — single channel

- Use the **Channel** spinner to select which of the 32 channels is shown.
- The rolling window always shows the last **10 seconds** of data.
- The x-axis shows time in seconds; the y-axis auto-scales to the signal.

### Live plot — all channels

- Click **Plot All Channels** to switch to the stacked overview.
- All 32 channels are displayed simultaneously with a small vertical offset
  between them so signals remain readable.
- Click **Single Channel View** to return to the single-channel plot.

### Switch signal mode

Use the **Signal Mode** dropdown to choose:

| Mode     | Description |
|----------|-------------|
| Original | Raw samples, no processing |
| Filtered | 4th-order Butterworth bandpass (20 – 450 Hz) |
| RMS      | Sliding-window RMS envelope of the filtered signal |

The mode applies to both the live VisPy plot and the offline Matplotlib plot.

### Offline inspection

1. Click **Disconnect** to stop streaming.
2. Click **Open Offline Plot (Matplotlib)** to open the inspection dialog.
3. In the dialog:
   - Choose a channel with the spinner.
   - Switch the mode with the dropdown.
   - Use the Matplotlib toolbar to zoom, pan, and save the plot.

---

## Signal processing parameters

### Bandpass filter

| Parameter       | Value    | Rationale |
|-----------------|----------|-----------|
| Filter type     | Butterworth | Maximally flat passband |
| Order           | 4        | Good roll-off without excessive ringing |
| Low cutoff      | 20 Hz    | Removes DC offset and movement artefacts |
| High cutoff     | 450 Hz   | Below Nyquist (1000 Hz) at 2000 Hz sampling rate |
| Phase           | Zero-phase (`filtfilt`) | No time delay in the output |

### RMS envelope

| Parameter    | Value   | Rationale |
|--------------|---------|-----------|
| Window       | 100 ms  | Standard EMG envelope extraction length |
| Centred      | Yes     | Symmetric ±50 ms window around each sample |
| Input        | Filtered signal | RMS is applied after bandpass filtering |

---

## Error handling

The application handles the following error cases without crashing:

- Wrong or unreachable port → status bar message, no crash.
- Server not running → `OSError` caught and displayed.
- Connection lost mid-stream → timer stops, offline plot is offered.
- Disconnect before any data is received → clear message, no offline button.
- Invalid channel or mode → values are validated before being passed to
  the ViewModel.

---

## Dependencies

See `requirements.txt`.

```
numpy>=1.26,<3
scipy>=1.12,<2
PySide6>=6.7,<7
vispy>=0.14,<1
matplotlib>=3.8,<4
```
