import hid

from csv_logger import CsvLogger
from hid_sample import HidSample
from datetime import datetime

class HidController:
    def __init__(self):
        self.device = None
        self.available_devices = {}
        self.logger = CsvLogger()
        self.is_logging = False

    def scan(self):
        """Returns a list of display names for the UI."""
        devices = hid.enumerate()
        self.available_devices = {}
        display_names = []

        for d in devices:
            name = f"{d.get('product_string', 'Unknown')} ({hex(d['vendor_id'])}:{hex(d['product_id'])})"
            path_key = f"{name} [{d['path'].decode('utf-8', errors='ignore')}]"
            self.available_devices[path_key] = d
            display_names.append(path_key)
        return display_names

    def connect(self, selection):
        """Attempts to open the device by its path key."""
        if selection not in self.available_devices:
            return False

        if self.device:
            self.device.close()

        try:
            target = self.available_devices[selection]
            self.device = hid.Device(path=target['path'])
          #  self.device.set_nonblocking(True)  # this attribute does not exist, the LLM just have   smoked some weed
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def read_sample(self):
        """Reads one packet and returns a HidSample object or None."""
        if not self.device:
            return None

        try:
            data = self.device.read(10)
            if data and len(data) == 10:
                return HidSample.from_bytes(bytes(data))
        except Exception as e:
            print(f"Read error: {e}")
            self.device = None  # Force disconnect on error
        return None

    def disconnect(self):
        if self.device:
            self.device.close()
            self.device = None

    def send_command(self, command_str):
        """Sends a string command to the HID device."""
        if not self.device:
            return False

        try:
            # Convert string to bytes
            data = command_str.encode('utf-8')

            # HID reports usually need to be a fixed size (e.g., 64 bytes)
            # Most STM32 custom HID examples use 64. Adjust if yours is different.
            report = list(data)
            report = report[:64] + [0] * (64 - len(report))

            # Send the data (HID requires the first byte to be the Report ID, usually 0)
            self.device.write([0] + report)
            return True
        except Exception as e:
            print(f"Write error: {e}")
            return False