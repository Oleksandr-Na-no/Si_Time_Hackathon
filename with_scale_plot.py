import customtkinter as ctk
import hid
from hid_sample import HidSample
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from tkinter import messagebox

# --- Appearance Settings ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HidApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Frequency Counter Pro")
        self.geometry("1280x640")

        # --- State Management ---
        self.device = None
        self.available_devices = {}
        self.max_points = 100
        self.y_data = deque([0] * self.max_points, maxlen=self.max_points)

        # --- Base Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # 1. SIDEBAR UI
        # ==========================================
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="HID CONTROL", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        # Device Selection Dropdown
        ctk.CTkLabel(self.sidebar, text="Select Device:", font=("Arial", 12)).pack(pady=(10, 0))
        self.device_combo = ctk.CTkComboBox(self.sidebar, values=["No Devices Found"])
        self.device_combo.pack(pady=10, padx=20, fill="x")

        # Connect Button
        self.connect_btn = ctk.CTkButton(
            self.sidebar,
            text="Connect",
            fg_color="#1f538d",
            command=self.handle_connect
        )
        self.connect_btn.pack(pady=5, padx=20, fill="x")

        # Refresh List Button
        self.refresh_btn = ctk.CTkButton(
            self.sidebar,
            text="Refresh List",
            fg_color="transparent",
            border_width=1,
            command=self.scan_devices
        )
        self.refresh_btn.pack(pady=5, padx=20, fill="x")

        # Visual Separator (Thin Frame)
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30")
        separator.pack(pady=20, fill="x", padx=20)

        # Navigation Buttons
        self.btn_dash = ctk.CTkButton(self.sidebar, text="Dashboard", command=self.show_dashboard)
        self.btn_dash.pack(pady=10, padx=20, fill="x")

        self.btn_raw = ctk.CTkButton(self.sidebar, text="Raw View", command=self.show_raw)
        self.btn_raw.pack(pady=10, padx=20, fill="x")

        # ==========================================
        # 2. MAIN CONTENT AREA
        # ==========================================
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        # Top Stats Bar
        self.stats_frame = ctk.CTkFrame(self.container, height=60)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.freq_label = ctk.CTkLabel(self.stats_frame, text="Freq: -- Hz", font=("Arial", 18, "bold"))
        self.freq_label.pack(side="left", padx=20)

        self.gate_label = ctk.CTkLabel(self.stats_frame, text="Gate: --", font=("Arial", 16))
        self.gate_label.pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(self.stats_frame, text="Disconnected", text_color="red",
                                         font=("Arial", 14, "bold"))
        self.status_label.pack(side="right", padx=20)

        # Initialize Plot and Raw Views
        self.setup_plot()
        self.raw_text = ctk.CTkTextbox(self.container, font=("Courier", 14))

        # Start operations
        self.scan_devices()
        self.update_loop()

    # ==========================================
    # 3. HARDWARE LOGIC
    # ==========================================
    def scan_devices(self):
        """Scans the system for HID devices."""
        devices = hid.enumerate()
        self.available_devices = {}
        display_names = []

        for d in devices:
            name = f"{d.get('product_string', 'Unknown')} ({hex(d['vendor_id'])}:{hex(d['product_id'])})"
            path_key = f"{name} [{d['path'].decode('utf-8', errors='ignore')}]"
            self.available_devices[path_key] = d
            display_names.append(path_key)

        if display_names:
            self.device_combo.configure(values=display_names)
            self.device_combo.set(display_names[0])
        else:
            self.device_combo.configure(values=["No Devices Found"])
            self.device_combo.set("No Devices Found")

        # Reset the connect button visually
        self.connect_btn.configure(text="Connect", state="normal", fg_color="#1f538d")

    def handle_connect(self):
        """Wrapper for the connect button click."""
        selection = self.device_combo.get()
        if selection and selection != "No Devices Found":
            self.connect_device(selection)

    def connect_device(self, selection):
        """Connects to the device and configures non-blocking reads."""
        if selection not in self.available_devices: return

        if self.device:
            self.device.close()

        try:
            target = self.available_devices[selection]
            self.device = hid.Device(path=target['path'])


            # Update UI
            self.status_label.configure(text="Connected", text_color="green")
            self.connect_btn.configure(text="Connected", state="disabled", fg_color="green")
            self.raw_text.insert("end", f"\n>>> Connected to {selection} <<<\n")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect:\n{e}")
            self.status_label.configure(text="Failed", text_color="red")

    # ==========================================
    # 4. PLOT & VIEW LOGIC
    # ==========================================
    def setup_plot(self):
        """Initializes the Matplotlib figure embedded in Tkinter."""
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')  # Match CTK Frame
        self.ax.set_facecolor('#1a1a1a')

        self.line, = self.ax.plot(range(self.max_points), list(self.y_data), color='#3a7ebf', linewidth=2)
        self.ax.set_ylim(0, 1000)
        self.ax.set_ylabel("Frequency (Hz)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.container)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def show_dashboard(self):
        self.raw_text.grid_forget()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def show_raw(self):
        self.canvas.get_tk_widget().grid_forget()
        self.raw_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    # ==========================================
    # 5. MAIN DATA LOOP
    # ==========================================
    def update_loop(self):
        """Reads data continuously without freezing the UI."""
        if self.device:
            try:
                data = self.device.read(10)

                # Verify we received exactly the packet size we expect
                if data and len(data) == 10:
                    sample = HidSample.from_bytes(bytes(data))

                    # 1. Update Top Labels
                    self.freq_label.configure(text=f"Freq: {sample.freq_hz} Hz")
                    self.gate_label.configure(text=f"Gate: {sample.gate_label()}")
                    print(sample.gate_label)

                    # 2. Update Plot Data
                    self.y_data.append(sample.freq_hz)
                    self.line.set_ydata(list(self.y_data))

                    # 3. Dynamic Autoscaling
                    current_max = max(self.y_data)
                    plot_limit = max(10, current_max * 1.15)  # 15% headroom
                    _, existing_max = self.ax.get_ylim()

                    # Scale up if exceeding, scale down if max drops significantly
                    if current_max > existing_max or current_max < (existing_max * 0.5):
                        self.ax.set_ylim(0, plot_limit)

                    self.canvas.draw_idle()

                    # 4. Update Raw Text View (keep it clean)
                    self.raw_text.insert("end", f"{sample}\n")
                    self.raw_text.see("end")  # Auto-scroll
                    if float(self.raw_text.index('end-1c')) > 50:
                        self.raw_text.delete("1.0", "2.0")

            except Exception as e:
                print(f"Read Loop Error: {e}")
                self.status_label.configure(text="Device Lost", text_color="red")
                self.connect_btn.configure(text="Connect", state="normal", fg_color="#1f538d")
                self.device = None

        # Repeat every 30ms (~33 FPS)
        self.after(30, self.update_loop)


if __name__ == "__main__":
    app = HidApp()
    app.mainloop()