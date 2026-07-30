# VisPy live plot widgets.
#   SingleChannelPlotWidget  — rolling plot for one channel
#   AllChannelsPlotWidget    — all 32 channels stacked with vertical offsets

import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QWidget
from vispy import scene


class SingleChannelPlotWidget(QWidget):
    """Rolling VisPy line plot for a single EMG channel."""

    LINE_COLOR = (0.1, 0.4, 0.85, 1.0)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the VisPy canvas with linked x/y axes and a placeholder line."""
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.canvas = scene.SceneCanvas(
            keys="interactive", show=False, bgcolor="white", size=(900, 400)
        )

        grid = self.canvas.central_widget.add_grid(margin=10)

        self._y_axis = scene.AxisWidget(orientation="left", font_size=9)
        self._x_axis = scene.AxisWidget(orientation="bottom", font_size=9)
        self._y_axis.width_max = 60
        self._x_axis.height_max = 40

        grid.add_widget(self._y_axis, row=0, col=0)
        self._view = grid.add_view(row=0, col=1)
        self._view.camera = "panzoom"
        grid.add_widget(self._x_axis, row=1, col=1)

        self._x_axis.link_view(self._view)
        self._y_axis.link_view(self._view)

        # placeholder line, replaced on every tick
        self._line = scene.Line(
            pos=np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32),
            color=self.LINE_COLOR,
            parent=self._view.scene,
            width=1.5,
        )

        layout.addWidget(self.canvas.native)

    def update_plot(self, x: np.ndarray, y: np.ndarray) -> None:
        """Push new (x, y) data to the canvas and dynamically rescale both axes."""
        x = np.asarray(x, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)

        if x.size < 2:
            return

        self._line.set_data(pos=np.column_stack((x, y)))

        # Dynamic Y-scaling: pad by 10% of the signal range so the line is never clipped
        y_range = y.max() - y.min()
        pad = max(1e-6, 0.1 * y_range)
        self._view.camera.set_range(
            x=(float(x[0]), float(x[-1])),
            y=(float(y.min()) - pad, float(y.max()) + pad),
        )


class AllChannelsPlotWidget(QWidget):
    """All 32 channels stacked vertically with a small offset between each."""

    COLORS = [
        (0.1, 0.4, 0.85, 0.9),
        (0.85, 0.2, 0.1, 0.9),
        (0.1, 0.7, 0.3, 0.9),
        (0.6, 0.1, 0.8, 0.9),
    ]

    CHANNEL_SPACING: float = 3.0  # normalised units between channels

    def __init__(self, n_channels: int = 32, parent: QWidget | None = None) -> None:
        """Build the VisPy canvas and create one Line visual per channel."""
        super().__init__(parent)

        self.n_channels = n_channels

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.canvas = scene.SceneCanvas(
            keys="interactive", show=False, bgcolor="#111111", size=(900, 600)
        )

        grid = self.canvas.central_widget.add_grid(margin=10)

        self._y_axis = scene.AxisWidget(
            orientation="left", font_size=8,
            axis_color="white", tick_color="white", text_color="white",
        )
        self._x_axis = scene.AxisWidget(
            orientation="bottom", font_size=8,
            axis_color="white", tick_color="white", text_color="white",
        )
        self._y_axis.width_max = 60
        self._x_axis.height_max = 40

        grid.add_widget(self._y_axis, row=0, col=0)
        self._view = grid.add_view(row=0, col=1)
        self._view.camera = "panzoom"
        grid.add_widget(self._x_axis, row=1, col=1)

        self._x_axis.link_view(self._view)
        self._y_axis.link_view(self._view)

        dummy = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        self._lines: list[scene.Line] = []
        for ch in range(self.n_channels):
            color = self.COLORS[ch % len(self.COLORS)]
            line = scene.Line(pos=dummy, color=color, parent=self._view.scene, width=1.0)
            self._lines.append(line)

        layout.addWidget(self.canvas.native)

    def update_plot(self, x: np.ndarray, data: np.ndarray) -> None:
        """Normalise and redraw all channel lines with vertical offsets."""
        x = np.asarray(x, dtype=np.float32)
        data = np.asarray(data, dtype=np.float32)

        if x.size < 2 or data.shape[1] < 2:
            return

        # normalise each channel so no single channel dominates visually
        ch_range = data.max(axis=1) - data.min(axis=1)
        ch_range[ch_range < 1e-9] = 1.0  # avoid div-by-zero for flat channels

        for ch_idx, line in enumerate(self._lines):
            if ch_idx >= data.shape[0]:
                break
            norm_y = (data[ch_idx] - data[ch_idx].mean()) / ch_range[ch_idx]
            # add offset so channels don't overlap
            pos = np.column_stack((x, norm_y + ch_idx * self.CHANNEL_SPACING)).astype(np.float32)
            line.set_data(pos=pos)

        y_min = -1.0
        y_max = (self.n_channels - 1) * self.CHANNEL_SPACING + 1.0
        self._view.camera.set_range(
            x=(float(x[0]), float(x[-1])),
            y=(y_min, y_max),
        )
