import customtkinter as ctk
import hid
from hid_sample import HidSample
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HidApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Frequency counter")
        self.geometry("1280x640")

        # --- State Management ---
        self.device = None
        self.available_devices = {}  # Maps display string -> device info dict
        self.max_points = 100
        self.y_data = deque([0] * self.max_points, maxlen=self.max_points)

        # --- Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="HID CONTROL", font=ctk.CTkFont(size=40, weight="bold")).pack(pady=20)

        # Device Selection UI
        ctk.CTkLabel(self.sidebar, text="Select Device:", font=("Arial", 12)).pack(pady=(10, 0))
        self.device_combo = ctk.CTkComboBox(self.sidebar, values=["No Devices Found"], command=self.connect_device)
        self.device_combo.pack(pady=10, padx=20,fill="x")

        self.refresh_btn = ctk.CTkButton(self.sidebar, text="Refresh List", fg_color="transparent", border_width=1,
                                         command=self.scan_devices)
        self.refresh_btn.pack(pady=5, padx=20,fill="x")

        # Create a thin frame to act as a separator
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30")
        separator.pack(pady=20, fill="x", padx=20)

        self.btn_dash = ctk.CTkButton(self.sidebar, text="Dashboard", command=self.show_dashboard)
        self.btn_dash.pack(pady=10, padx=20)

        self.btn_raw = ctk.CTkButton(self.sidebar, text="Raw View", command=self.show_raw)
        self.btn_raw.pack(pady=10, padx=20)

        # --- Main Content ---
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        self.stats_frame = ctk.CTkFrame(self.container, height=60)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.freq_label = ctk.CTkLabel(self.stats_frame, text="Freq: -- Hz", font=("Arial", 16))
        self.freq_label.pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(self.stats_frame, text="Disconnected", text_color="red")
        self.status_label.pack(side="right", padx=20)

        self.setup_plot()
        self.raw_text = ctk.CTkTextbox(self.container)

        # Initial scan and loop
        self.scan_devices()
        self.update_loop()

    def scan_devices(self):
        """Scans system for HID devices and updates the combobox."""
        devices = hid.enumerate()
        self.available_devices = {}
        display_names = []

        for d in devices:
            # Create a readable name
            name = f"{d['product_string'] or 'Unknown'} ({hex(d['vendor_id'])}:{hex(d['product_id'])})"
            # Use path as unique identifier to handle multiple identical devices
            path_key = f"{name} [{d['path'].decode()}]"
            self.available_devices[path_key] = d
            display_names.append(path_key)

        if display_names:
            self.device_combo.configure(values=display_names)
            self.device_combo.set(display_names[0])
        else:
            self.device_combo.configure(values=["No Devices Found"])
            self.device_combo.set("No Devices Found")

    def connect_device(self, selection):
        """Attempts to open the selected device."""
        if selection not in self.available_devices:
            return

        # Close existing device
        if self.device:
            self.device.close()

        try:
            target = self.available_devices[selection]
            self.device = hid.Device(path=target['path'])

            self.status_label.configure(text=f"Connected: {hex(target['product_id'])}", text_color="green")
            self.raw_text.insert("end", f"--- Connected to {selection} ---\n")
        except Exception as e:
            self.status_label.configure(text="Connection Failed", text_color="red")
            print(f"Error: {e}")

    def setup_plot(self):
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
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
            try:
                data = self.device.read(10)
                if data:
                    sample = HidSample.from_bytes(bytes(data))
                    self.freq_label.configure(text=f"Freq: {sample.freq_hz} Hz")
                    self.y_data.append(sample.freq_hz)
                    self.line.set_ydata(list(self.y_data))
                    self.canvas.draw_idle()

                    self.raw_text.insert("end", f"{sample}\n")
                    if float(self.raw_text.index('end-1c')) > 50:
                        self.raw_text.delete("1.0", "2.0")
            except Exception:
                self.status_label.configure(text="Device is nor right or now working", text_color="red")
                self.device = None

        self.after(30, self.update_loop)


if __name__ == "__main__":
    app = HidApp()
    app.mainloop()