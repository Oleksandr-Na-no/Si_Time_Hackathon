import sys
import queue
from datetime import datetime
import hid
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QComboBox, QPushButton, QLineEdit,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

# ---------------------------------------------------------
# Ваш оригінальний HIDReaderThread залишається без змін
# ---------------------------------------------------------
class HIDReaderThread(QThread):
    """
    Ізольований робочий потік для неблокуючого зчитування даних.
    """
    data_received = pyqtSignal(str)
    sample_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, device_path: bytes):
        super().__init__()
        self.device_path = device_path
        self.is_running = True
        self.active_device = None
        self._rx_buffer = bytearray()
        self._tx_queue = queue.Queue()

    @staticmethod
    def _try_parse_sample(decoded_line: str):
        if not decoded_line.startswith("@"):
            return None
        parts = decoded_line.split(",")
        if len(parts) != 5:
            return None
        if parts[0] not in ("@S", "@T"):
            return None
        try:
            sample = {
                "tag": parts[0][1],
                "seq": int(parts[1]),
                "tick_ms": int(parts[2]),
                "freq_hz": int(parts[3]),
                "gate_index": int(parts[4]),
            }
        except ValueError:
            return None

        gate_map = {0: "0.1s", 1: "1s", 2: "10s"}
        sample["gate_label"] = gate_map.get(sample["gate_index"], str(sample["gate_index"]))
        return sample

    def run(self):
        try:
            self.active_device = hid.device()
            self.active_device.open_path(self.device_path)
            self.active_device.set_nonblocking(1)

            while self.is_running:
                self._flush_pending_commands()
                data_payload = self.active_device.read(64)

                if data_payload:
                    raw_bytes = bytes(data_payload)
                    trimmed_bytes = raw_bytes.rstrip(b"\x00")
                    if not trimmed_bytes:
                        continue

                    self._rx_buffer.extend(trimmed_bytes)
                    self._rx_buffer = self._rx_buffer.replace(b"\r", b"\n")

                    while True:
                        newline_index = self._rx_buffer.find(b"\n")
                        if newline_index < 0:
                            if len(self._rx_buffer) > 512:
                                self._rx_buffer.clear()
                            break

                        line_bytes = bytes(self._rx_buffer[:newline_index]).strip()
                        del self._rx_buffer[: newline_index + 1]

                        if not line_bytes:
                            continue

                        decoded_text = line_bytes.decode("utf-8", errors="replace")
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        formatted_output = f"[{timestamp}] {decoded_text}"
                        
                        self.data_received.emit(formatted_output)

                        sample = self._try_parse_sample(decoded_text)
                        if sample is not None:
                            self.sample_received.emit(sample)
                else:
                    self.msleep(10)

        except Exception as e:
            self.error_occurred.emit(f"Hardware Exception: {str(e)}")
        finally:
            if self.active_device:
                try:
                    self.active_device.close()
                except Exception:
                    pass

    def enqueue_command(self, command: str):
        if command is None: return
        cmd = command.strip()
        if not cmd: return
        self._tx_queue.put(cmd)

    def _flush_pending_commands(self):
        if self.active_device is None: return
        for _ in range(4):
            try:
                cmd = self._tx_queue.get_nowait()
            except queue.Empty:
                break
            self._write_command(cmd)

    def _write_command(self, command: str):
        payload = (command + "\r\n").encode("ascii", errors="ignore")[:64]
        report_with_id = bytearray(65)
        report_with_id[0] = 0
        report_with_id[1 : 1 + len(payload)] = payload
        try:
            self.active_device.write(report_with_id)
            return
        except Exception:
            pass
        report_no_id = bytearray(64)
        report_no_id[: len(payload)] = payload
        self.active_device.write(report_no_id)

    def stop_reading(self):
        self.is_running = False
        self.wait()


# ---------------------------------------------------------
# Новий графічний інтерфейс на основі макета
# ---------------------------------------------------------
class ModernHackathonGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SiTime Frequency Monitor")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #F8F9FA;") # Світлий фон як на макеті

        self.device_mapping = {}
        self.reader_thread = None
        
        # Дані для графіка
        self.plot_time = []
        self.plot_freq = []
        self.time_counter = 0

        self._construct_ui()
        self._enumerate_hid_devices()

    def _construct_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- ВЕРХНЯ ПАНЕЛЬ: Вибір пристрою ---
        top_layout = QHBoxLayout()
        self.combo_devices = QComboBox()
        self.combo_devices.setStyleSheet("""
            QComboBox {
                border: 2px solid #8B5CF6;
                border-radius: 8px;
                padding: 5px 15px;
                background: white;
                font-size: 14px;
            }
        """)
        top_layout.addWidget(self.combo_devices, stretch=1)

        self.btn_toggle = QPushButton("Підключитись")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6; color: white;
                border-radius: 8px; padding: 8px 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        self.btn_toggle.clicked.connect(self._toggle_reading)
        top_layout.addWidget(self.btn_toggle)
        main_layout.addLayout(top_layout)

        # --- СЕРЕДНЯ ПАНЕЛЬ: Графік (pyqtgraph) ---
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('w')
        self.graphWidget.showGrid(x=True, y=True, alpha=0.3)
        self.graphWidget.getAxis('left').setPen('grey')
        self.graphWidget.getAxis('bottom').setPen('grey')
        # Стилізація лінії графіка (синя, як на макеті)
        pen = pg.mkPen(color=(59, 130, 246), width=2)
        self.data_line = self.graphWidget.plot(self.plot_time, self.plot_freq, pen=pen)
        main_layout.addWidget(self.graphWidget, stretch=1)

        # --- НИЖНЯ ПАНЕЛЬ: Керування ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Блок "Час вимірювання"
        time_meas_layout = QVBoxLayout()
        lbl_time = QLabel("Час вимірювання")
        lbl_time.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        time_meas_layout.addWidget(lbl_time)

        btn_group_layout = QHBoxLayout()
        self.btn_01s = QPushButton("0.1 s")
        self.btn_1s = QPushButton("1 S")
        self.btn_10s = QPushButton("10 S")
        
        # Загальний стиль для кнопок-пігулок
        self.pill_style_inactive = """
            QPushButton {
                background-color: #EFE8FF; color: #5B21B6;
                border-radius: 15px; padding: 8px 20px; font-weight: bold;
            }
        """
        self.pill_style_active = """
            QPushButton {
                background-color: #6D6875; color: white;
                border-radius: 15px; padding: 8px 20px; font-weight: bold;
            }
        """
        for btn in [self.btn_01s, self.btn_1s, self.btn_10s]:
            btn.setStyleSheet(self.pill_style_inactive)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_group_layout.addWidget(btn)

        # По замовчуванню активна перша
        self.btn_01s.setStyleSheet(self.pill_style_active)
        
        # Прив'язка команд (замініть 'gate X' на реальні команди вашого МК)
        self.btn_01s.clicked.connect(lambda: self._set_gate(self.btn_01s, "gate 0"))
        self.btn_1s.clicked.connect(lambda: self._set_gate(self.btn_1s, "gate 1"))
        self.btn_10s.clicked.connect(lambda: self._set_gate(self.btn_10s, "gate 2"))
        
        time_meas_layout.addLayout(btn_group_layout)
        bottom_layout.addLayout(time_meas_layout)
        
        bottom_layout.addSpacing(50)

        # Блок "Тригер" та "Частота"
        trigger_freq_layout = QVBoxLayout()
        
        # lbl_freq_title = QLabel("Частота")
        # lbl_freq_title.setStyleSheet("color: #6B7280; font-size: 16px;")
        # trigger_freq_layout.addWidget(lbl_freq_title)

        action_row = QHBoxLayout()
        
        self.btn_trigger = QPushButton("Тригер")
        self.btn_trigger.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; color: #8B5CF6;
                border: 2px solid #EFE8FF; border-radius: 20px;
                padding: 10px 25px; font-weight: bold; font-size: 16px;
            }
            QPushButton:hover { background-color: #EFE8FF; }
        """)
        self.btn_trigger.clicked.connect(lambda: self._send_command("mode direct"))
        action_row.addWidget(self.btn_trigger)

        self.val_freq = QLineEdit("-- Гц")
        self.val_freq.setReadOnly(True)
        self.val_freq.setStyleSheet("""
            QLineEdit {
                background-color: white; border: 1px solid #D1D5DB;
                border-radius: 8px; padding: 10px; font-size: 18px; color: #1F2937;
            }
        """)
        self.val_freq.setFixedWidth(150)
        action_row.addWidget(self.val_freq)
        
        trigger_freq_layout.addLayout(action_row)
        bottom_layout.addLayout(trigger_freq_layout)

        main_layout.addLayout(bottom_layout)

    def _set_gate(self, active_btn, command):
        """Змінює стиль кнопок і надсилає команду вибору часу вимірювання."""
        for btn in [self.btn_01s, self.btn_1s, self.btn_10s]:
            btn.setStyleSheet(self.pill_style_inactive)
        active_btn.setStyleSheet(self.pill_style_active)
        self._send_command(command)

    def _enumerate_hid_devices(self):
        self.combo_devices.clear()
        self.device_mapping.clear()
        try:
            for dev in hid.enumerate():
                vid = dev.get("vendor_id", 0)
                pid = dev.get("product_id", 0)
                product = dev.get("product_string", "Unknown")
                path = dev.get("path")
                display_string = f"[{vid:04X}:{pid:04X}] - {product}"
                if path:
                    self.device_mapping[display_string] = path
                    self.combo_devices.addItem(display_string)
        except Exception as e:
            print(f"Помилка пошуку пристроїв: {e}")

    def _toggle_reading(self):
        if self.reader_thread is None or not self.reader_thread.isRunning():
            self._start_reading()
        else:
            self._stop_reading()

    def _start_reading(self):
        selected_text = self.combo_devices.currentText()
        if not selected_text or selected_text not in self.device_mapping:
            return

        device_path = self.device_mapping[selected_text]
        self.reader_thread = HIDReaderThread(device_path)
        self.reader_thread.sample_received.connect(self._update_live_sample)
        self.reader_thread.start()

        self.btn_toggle.setText("Відключитись")
        self.combo_devices.setEnabled(False)
        self._send_command("stream on")

    def _stop_reading(self):
        if self.reader_thread and self.reader_thread.isRunning():
            self.reader_thread.stop_reading()
            self.reader_thread = None

        self.btn_toggle.setText("Підключитись")
        self.combo_devices.setEnabled(True)

    def _send_command(self, command: str):
        if self.reader_thread and self.reader_thread.isRunning():
            self.reader_thread.enqueue_command(command)

    def _update_live_sample(self, sample: dict):
        """Оновлює поле частоти та малює графік."""
        freq_hz = sample.get("freq_hz", 0)
        
        # Оновлення тексту
        if freq_hz >= 1000000:
            self.val_freq.setText(f"{freq_hz / 1000000:.3f} МГц")
        else:
            self.val_freq.setText(f"{freq_hz} Гц")

        # Оновлення графіка
        self.time_counter += 1
        self.plot_time.append(self.time_counter)
        self.plot_freq.append(freq_hz)

        # Зберігаємо лише останні 100 точок, щоб графік не переповнювався
        if len(self.plot_time) > 100:
            self.plot_time.pop(0)
            self.plot_freq.pop(0)

        self.data_line.setData(self.plot_time, self.plot_freq)

    def closeEvent(self, event):
        if self.reader_thread and self.reader_thread.isRunning():
            self.reader_thread.stop_reading()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernHackathonGUI()
    window.show()
    sys.exit(app.exec())