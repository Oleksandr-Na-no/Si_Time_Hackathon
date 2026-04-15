import csv
from datetime import datetime


class CsvLogger:
    def __init__(self):
        self.file = None
        self.writer = None

    def start(self):
        """Creates a new CSV file with a timestamped name."""
        # Format: log_2026-04-15_20-30-05.csv
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"freq_log_{timestamp}.csv"

        self.file = open(filename, mode='w', newline='')
        self.writer = csv.writer(self.file)

        # Write the header with a 'Date' and 'Time' column
        self.writer.writerow(["Date", "Time", "Frequency (Hz)", "Gate"])
        return filename

    def log(self, sample):
        """Writes a single row of data to the CSV."""
        if self.writer:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S.%f")[:-3]  # Includes milliseconds

            self.writer.writerow([
                date_str,
                time_str,
                sample.freq_hz,
                sample.gate_label()  # Using parentheses as discussed
            ])

    def stop(self):
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None