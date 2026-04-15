import tkinter as tk
from tkinter import messagebox
import hid
from hid_sample import HidSample
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque


class HidGui:
    def __init__(self, root):
        self.root = root
        self.root.title("HID Device Monitor & Plotter")

        # --- Data Storage ---
        self.max_points = 50
        self.x_data = list(range(self.max_points))
        self.y_data = deque([0] * self.max_points, maxlen=self.max_points)

        # --- Device Setup ---
        try:
            self.device = hid.Device(0xc0de, 0xcafe)

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not find device: {e}")
            self.root.destroy()
            return

        # --- UI Layout ---
        top_frame = tk.Frame(root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.freq_var = tk.StringVar(value="Frequency: -- Hz")
        tk.Label(top_frame, textvariable=self.freq_var, font=('Arial', 12, 'bold')).pack(side=tk.LEFT)

        self.gate_var = tk.StringVar(value="Gate: --")
        tk.Label(top_frame, textvariable=self.gate_var, font=('Arial', 12), fg="blue").pack(side=tk.RIGHT)

        # --- Plotting Setup ---
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.ax.set_title("Real-time Frequency (Hz)")
        self.line, = self.ax.plot(self.x_data, list(self.y_data), color='green')
        self.ax.set_ylim(0, 1000)  # Adjust this based on your expected Hz range

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.update_data()

    def update_data(self):
        try:
            # Read data (non-blocking)
            data = self.device.read(10)

            if data:
                sample = HidSample.from_bytes(bytes(data))

                # Update Text
                self.freq_var.set(f"Frequency: {sample.freq_hz} Hz")
                self.gate_var.set(f"Gate: {sample.gate_label}")

                # Update Plot Data
                self.y_data.append(sample.freq_hz)
                self.line.set_ydata(list(self.y_data))

                # Rescale Y axis automatically if values go out of bounds
                current_max = max(self.y_data)
                if current_max > self.ax.get_ylim()[1]:
                    self.ax.set_ylim(0, current_max * 1.2)

                self.canvas.draw_idle()  # Redraw the plot

        except Exception as e:
            print(f"Error: {e}")

        # High-speed refresh (approx 30 FPS)
        self.root.after(33, self.update_data)


if __name__ == "__main__":
    root = tk.Tk()
    app = HidGui(root)
    root.mainloop()