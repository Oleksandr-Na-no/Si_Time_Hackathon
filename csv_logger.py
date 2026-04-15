import csv
from datetime import datetime


class CsvLogger:
    def __init__(self):
        self.file = None
        self.writer = None

    def start(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"records/freq_record_{timestamp}.csv"
        # We open the file and keep it open
        self.file = open(filename, mode='w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["Date", "Time", "Frequency (Hz)", "Gate"])

        # Force the header to be written immediately
        self.file.flush()
        return filename

    def log(self, sample):
        if self.writer and self.file:
            now = datetime.now()
            self.writer.writerow([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S.%f")[:-3],
                sample.freq_hz,
                sample.gate_label()
            ])

            # --- THE MAGIC FIX ---
            # 1. Flush the internal Python buffer to the OS
            self.file.flush()
            # 2. (Optional) Force the OS to write to the physical drive
            # os.fsync(self.file.fileno())
            # Note: fsync can slow down high-speed apps, flush is usually enough.

    def stop(self):
        if self.file:
            self.file.flush()  # Final flush
            self.file.close()
            self.file = None
            self.writer = None