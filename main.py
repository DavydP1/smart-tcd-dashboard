import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg

# --- Стилістика UI (Dark Blue & White-Blue Medical Theme) ---
DARK_BG = "#0B132B"
PANEL_BG = "#1C2541"
TEXT_COLOR = "#FFFFFF"
ACCENT_BLUE = "#00B4D8"
CYAN_HIGHLIGHT = "#90E0EF"
LINE_COLOR = "#48CAE4"

STYLE_SHEET = f"""
    QMainWindow {{
        background-color: {DARK_BG};
    }}
    QFrame#Card {{
        background-color: {PANEL_BG};
        border-radius: 10px;
        border: 1px solid #3A506B;
    }}
    QLabel {{
        color: {TEXT_COLOR};
        font-family: 'Segoe UI', Arial, sans-serif;
    }}
"""

class MetricCard(QFrame):
    def __init__(self, title, unit, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {CYAN_HIGHLIGHT};")
        
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {ACCENT_BLUE};")
        self.value_label.setAlignment(Qt.AlignCenter)
        
        self.unit_label = QLabel(unit)
        self.unit_label.setStyleSheet("font-size: 11px; color: #8D99AE;")
        self.unit_label.setAlignment(Qt.AlignRight)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.unit_label)

    def set_value(self, val_str):
        self.value_label.setText(val_str)

class TCDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartTCD Pro | Transcranial Doppler Monitor")
        self.resize(1200, 800)
        self.setStyleSheet(STYLE_SHEET)
        
        self.fs = 8000
        self.chunk_size = 512
        self.time_phase = 0.0
        
        self.raw_signal_buffer = np.zeros(2048)
        self.spectrogram_history = np.zeros((128, 100))
        self.pi_trend_buffer = np.full(100, 0.85)
        
        self.init_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(40)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        header = QLabel("TRANSCRANIAL DOPPLER MONITORING SYSTEM (CAROTID TEST)")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_COLOR}; letter-spacing: 2px;")
        main_layout.addWidget(header)
        
        metrics_layout = QHBoxLayout()
        self.card_psv = MetricCard("PSV (Peak Systolic)", "cm/s")
        self.card_edv = MetricCard("EDV (End Diastolic)", "cm/s")
        self.card_pi = MetricCard("PI (Pulsatility Index)", "norm: 0.6-1.0")
        self.card_hr = MetricCard("HR (Heart Rate)", "BPM")
        
        metrics_layout.addWidget(self.card_psv)
        metrics_layout.addWidget(self.card_edv)
        metrics_layout.addWidget(self.card_pi)
        metrics_layout.addWidget(self.card_hr)
        main_layout.addLayout(metrics_layout)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        
        self.raw_plot = pg.PlotWidget(title="<b>Raw Doppler Audio Signal (Wall Filtered > 150 Hz)</b>")
        self.configure_plot(self.raw_plot)
        self.raw_curve = self.raw_plot.plot(pen=pg.mkPen(color=LINE_COLOR, width=1.5))
        grid_layout.addWidget(self.raw_plot, 0, 0)
        
        self.spec_plot = pg.PlotWidget(title="<b>Real-time FFT Spectrogram (Blood Flow Velocity)</b>")
        self.configure_plot(self.spec_plot)
        self.img_item = pg.ImageItem()
        self.spec_plot.addItem(self.img_item)
        
        cmap = pg.ColorMap(
            pos=np.array([0.0, 0.3, 0.7, 1.0]),
            color=np.array([
                [11, 19, 43, 255],
                [28, 37, 65, 255],
                [72, 202, 228, 255],
                [255, 255, 255, 255]
            ], dtype=np.uint8)
        )
        self.img_item.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
        grid_layout.addWidget(self.spec_plot, 0, 1)
        
        self.trend_plot = pg.PlotWidget(title="<b>PI Trend (Real-Time Aggregation)</b>")
        self.configure_plot(self.trend_plot)
        self.trend_curve = self.trend_plot.plot(pen=pg.mkPen(color=ACCENT_BLUE, width=2))
        
        norm_region = pg.LinearRegionItem(values=[0.6, 1.0], orientation=pg.LinearRegionItem.Horizontal,
                                          brush=pg.mkBrush(0, 180, 216, 30), movable=False)
        self.trend_plot.addItem(norm_region)
        grid_layout.addWidget(self.trend_plot, 1, 0, 1, 2)
        
        main_layout.addLayout(grid_layout)

    def configure_plot(self, plot_widget):
        plot_widget.setBackground(PANEL_BG)
        plot_widget.showGrid(x=True, y=True, alpha=0.2)
        plot_Widget_axis_left = plot_widget.getAxis('left').setPen(pg.mkPen(color="#8D99AE"))
        plot_widget.getAxis('bottom').setPen(pg.mkPen(color="#8D99AE"))

    def generate_synthetic_data(self):
        t = np.linspace(self.time_phase, self.time_phase + 0.05, self.chunk_size)
        self.time_phase += 0.05
        pulse = np.sin(2 * np.pi * 1.2 * t) ** 4
        base_freq = 600 + pulse * 1200
        signal = np.sin(2 * np.pi * base_freq * t) + 0.2 * np.random.normal(size=self.chunk_size)
        filtered_signal = np.where(np.abs(signal) < 0.15, 0, signal)
        return filtered_signal, pulse[-1]

    def update_loop(self):
        chunk, pulse_val = self.generate_synthetic_data()
        
        self.raw_signal_buffer = np.roll(self.raw_signal_buffer, -self.chunk_size)
        self.raw_signal_buffer[-self.chunk_size:] = chunk
        self.raw_curve.setData(self.raw_signal_buffer)
        
        fft_data = np.abs(np.fft.rfft(chunk * np.hanning(self.chunk_size)))[:128]
        fft_data = np.log10(fft_data + 1.0)
        
        self.spectrogram_history = np.roll(self.spectrogram_history, -1, axis=1)
        self.spectrogram_history[:, -1] = fft_data
        self.img_item.setImage(self.spectrogram_history, autoLevels=False, levels=[0, 1.5])
        
        psv = float(65.0 + pulse_val * 35.0 + np.random.uniform(-1.5, 1.5))
        edv = float(28.0 + pulse_val * 6.0 + np.random.uniform(-1.0, 1.0))
        mean_v = (psv + 2 * edv) / 3.0
        pi = (psv - edv) / mean_v
        
        self.card_psv.set_value(f"{psv:.1f}")
        self.card_edv.set_value(f"{edv:.1f}")
        self.card_pi.set_value(f"{pi:.2f}")
        self.card_hr.set_value("72")
        
        self.pi_trend_buffer = np.roll(self.pi_trend_buffer, -1)
        self.pi_trend_buffer[-1] = pi
        self.trend_curve.setData(self.pi_trend_buffer)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TCDDashboard()
    window.show()
    sys.exit(app.exec_())
