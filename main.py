import customtkinter as ctk
from logic import HidController
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class HidApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Frequency Counter Pro")
        self.geometry("1280x640")

        # Initialize Logic
        self.logic = HidController()

        # Data storage
        self.max_points = 100
        self.y_data = deque([0] * self.max_points, maxlen=self.max_points)

        self._build_sidebar()
        self._build_main_content()

        # Initial scan
        self.scan_devices()
        self.update_loop()

    def _build_sidebar(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="HID CONTROL", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        # Device Selection
        self.device_combo = ctk.CTkComboBox(self.sidebar, values=["No Devices Found"], width=220)
        self.device_combo.pack(pady=10, padx=20)

        self.connect_btn = ctk.CTkButton(self.sidebar, text="Connect", command=self.on_connect_clicked)
        self.connect_btn.pack(pady=5, padx=20)

        self.refresh_btn = ctk.CTkButton(self.sidebar, text="Refresh List", fg_color="transparent",
                                         border_width=1, command=self.scan_devices)
        self.refresh_btn.pack(pady=5, padx=20)

        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").pack(pady=20, fill="x", padx=20)

        ctk.CTkButton(self.sidebar, text="Dashboard", command=self.show_dashboard).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="Raw View", command=self.show_raw).pack(pady=10, padx=20)

    def _build_main_content(self):
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        # Stats bar
        self.stats_frame = ctk.CTkFrame(self.container, height=60)
        self.stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.freq_label = ctk.CTkLabel(self.stats_frame, text="Freq: -- Hz", font=("Arial", 18, "bold"))
        self.freq_label.pack(side="left", padx=20)

        self.gate_label = ctk.CTkLabel(self.stats_frame, text="Gate: --", font=("Arial", 16))
        self.gate_label.pack(side="left", padx=20)

        self.status_label = ctk.CTkLabel(self.stats_frame, text="Disconnected", text_color="red")
        self.status_label.pack(side="right", padx=20)

        self._setup_plot()
        self.raw_text = ctk.CTkTextbox(self.container, font=("Courier", 14))

    def _setup_plot(self):
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#1a1a1a')
        self.line, = self.ax.plot(range(self.max_points), list(self.y_data), color='#3a7ebf', linewidth=2)
        self.ax.set_ylim(0, 1000)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.container)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def scan_devices(self):
        names = self.logic.scan()
        if names:
            self.device_combo.configure(values=names)
            self.device_combo.set(names[0])
        self.connect_btn.configure(text="Connect", state="normal", fg_color="#1f538d")

    def on_connect_clicked(self):
        selection = self.device_combo.get()
        if self.logic.connect(selection):
            self.status_label.configure(text="Connected", text_color="green")
            self.connect_btn.configure(text="Connected", state="disabled", fg_color="green")
        else:
            messagebox.showerror("Error", "Could not connect to device.")

    def show_dashboard(self):
        self.raw_text.grid_forget()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def show_raw(self):
        self.canvas.get_tk_widget().grid_forget()
        self.raw_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def update_loop(self):
        sample = self.logic.read_sample()
        if sample:
            self.freq_label.configure(text=f"Freq: {sample.freq_hz} Hz")
            self.gate_label.configure(text=f"Gate: {sample.gate_label()}")

            # Update Plot
            self.y_data.append(sample.freq_hz)
            self.line.set_ydata(list(self.y_data))

            # Autoscaling
            curr_max = max(self.y_data)
            limit = max(10, curr_max * 1.15)
            _, ex_max = self.ax.get_ylim()
            if curr_max > ex_max or curr_max < (ex_max * 0.5):
                self.ax.set_ylim(0, limit)
            self.canvas.draw_idle()

            # Raw Log
            self.raw_text.insert("end", f"{sample}\n")
            self.raw_text.see("end")
            if float(self.raw_text.index('end-1c')) > 50:
                self.raw_text.delete("1.0", "2.0")

        elif self.logic.device is None and self.status_label.cget("text") == "Connected":
            self.status_label.configure(text="Disconnected", text_color="red")
            self.connect_btn.configure(text="Connect", state="normal", fg_color="#1f538d")

        self.after(30, self.update_loop)


if __name__ == "__main__":
    app = HidApp()
    app.mainloop()