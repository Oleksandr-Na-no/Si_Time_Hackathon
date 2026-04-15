import customtkinter as ctk
import hid
from hid_sample import HidSample
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

# Set the appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HidApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HID Analyzer Pro")
        self.geometry("900x500")

        # --- Device Setup ---
        try:
            self.device = hid.Device(0xc0de, 0xcafe)
            self.device.set_nonblocking(True)
        except Exception as e:
            print(f"Connection Error: {e}")
            self.device = None

        # --- Data Prep ---
        self.max_points = 100
        self.y_data = deque([0] * self.max_points, maxlen=self.max_points)

        # --- Layout Grid ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="HID SENSOR", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20, padx=20)

        self.btn_dash = ctk.CTkButton(self.sidebar, text="Dashboard", command=self.show_dashboard)
        self.btn_dash.pack(pady=10, padx=20)

        self.btn_raw = ctk.CTkButton(self.sidebar, text="Raw View", command=self.show_raw)
        self.btn_raw.pack(pady=10, padx=20)

        # --- Main Content Area ---
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        # Header Stats
        self.stats_frame = ctk.CTkFrame(self.container, height=60)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.freq_label = ctk.CTkLabel(self.stats_frame, text="Freq: 0 Hz", font=("Arial", 16))
        self.freq_label.pack(side="left", padx=20)

        self.gate_label = ctk.CTkLabel(self.stats_frame, text="Gate: --", font=("Arial", 16))
        self.gate_label.pack(side="right", padx=20)

        # Plot Area (Dashboard View)
        self.setup_plot()

        # Raw Text Area (Hidden by default)
        self.raw_text = ctk.CTkTextbox(self.container)

        self.update_loop()

    def setup_plot(self):
        # Matplotlib Dark Style
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')  # Matches CTK Frame
        self.ax.set_facecolor('#1a1a1a')

        self.line, = self.ax.plot(range(self.max_points), list(self.y_data), color='#1f538d', linewidth=2)
        self.ax.set_ylim(0, 1000)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.container)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def show_dashboard(self):
        self.raw_text.grid_forget()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def show_raw(self):
        self.canvas.get_tk_widget().grid_forget()
        self.raw_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def update_loop(self):
        if self.device:
            data = self.device.read(10)
            if data:
                sample = HidSample.from_bytes(bytes(data))

                # Update Labels
                self.freq_label.configure(text=f"Freq: {sample.freq_hz} Hz")
                self.gate_label.configure(text=f"Gate: {sample.gate_label}")

                # Update Plot
                self.y_data.append(sample.freq_hz)
                self.line.set_ydata(list(self.y_data))
                self.canvas.draw_idle()

                # Update Raw Log (Keep only last 20 lines)
                self.raw_text.insert("end", f"{sample}\n")
                if float(self.raw_text.index('end-1c')) > 20:
                    self.raw_text.delete("1.0", "2.0")

        self.after(30, self.update_loop)


if __name__ == "__main__":
    app = HidApp()
    app.mainloop()