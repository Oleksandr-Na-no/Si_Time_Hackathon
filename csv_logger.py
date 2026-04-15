import csv
from datetime import datetime

class CsvLogger:
    def __init__(self):
        self.file = None
        self.writer = None

    def start(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"records/freq_log_{timestamp}.csv"
        self.file = open(filename, mode='w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["Date", "Time", "Frequency (Hz)", "Gate"])
        return filename

    def log(self, sample):
        if self.writer:
            now = datetime.now()
            self.writer.writerow([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S.%f")[:-3],
                sample.freq_hz,
                sample.gate_label()
            ])

    def stop(self):
        if self.file:
            self.file.close()
            self.file = None