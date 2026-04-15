from datetime import datetime


class ErrorLogger:
    def __init__(self, filename="logs/error_log.txt"):
        self.filename = filename

    def log_error(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filename, "a") as f:
            f.write(f"[{timestamp}] ERROR: {message}\n")