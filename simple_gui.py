import tkinter as tk
from tkinter import messagebox
import hid
from hid_sample import HidSample


class HidGui:
    def __init__(self, root):
        self.root = root
        self.root.title("HID Device Monitor")
        self.root.geometry("400x250")

        # --- Device Setup ---
        try:
            self.device = hid.Device(0xc0de, 0xcafe)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not find device: {e}")
            self.root.destroy()
            return

        # --- UI Elements ---
        tk.Label(root, text="HID Data Stream", font=('Arial', 14, 'bold')).pack(pady=10)

        # Frequency Display
        self.freq_var = tk.StringVar(value="Frequency: -- Hz")
        tk.Label(root, textvariable=self.freq_var, font=('Arial', 12)).pack(pady=5)

        # Gate Label Display
        self.gate_var = tk.StringVar(value="Gate: --")
        tk.Label(root, textvariable=self.gate_var, font=('Arial', 12), fg="blue").pack(pady=5)

        # Raw Output Display
        self.raw_var = tk.StringVar(value="Waiting for data...")
        tk.Label(root, textvariable=self.raw_var, font=('Courier', 10), wraplength=350).pack(pady=20)

        # Start the polling loop
        self.update_data()

    def update_data(self):
        try:
            # Read 10 bytes (non-blocking if possible, or very fast)
            data = self.device.read(10)

            if data:
                sample = HidSample.from_bytes(bytes(data))

                # Update the UI variables
                self.freq_var.set(f"Frequency: {sample.freq_hz} Hz")
                self.gate_var.set(f"Gate Label: {sample.gate_label}")
                self.raw_var.set(f"Raw: {sample}")

        except Exception as e:
            self.raw_var.set(f"Read Error: {e}")

        # Schedule the next read in 100ms (10 times per second)
        self.root.after(100, self.update_data)


if __name__ == "__main__":
    root = tk.Tk()
    app = HidGui(root)
    root.mainloop()