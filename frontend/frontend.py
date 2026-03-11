import tkinter as tk
import time
import itertools
from PIL import Image, ImageTk
from tkinter import ttk, PhotoImage
from backend.SimulationParameters import SimulationParams
from backend.SimulationEngine import SimulationEngine, EmergencyType
from backend.report import read_last_report, DEFAULT_STATS_CSV_PATH, append_report_csv
from backend.statistics import Statistics
from backend.queues import HoldingQueue, TakeOffQueue
from backend.runway import Runway
from backend.airport import Airport
from backend.aircraft import Aircraft

import os
import sys

def resource_path(relative_path):
    """Return absolute path to resource (works for dev and PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Define the main class for the user interface
class AirportUI:
    # Initialize the UI with the root window and simulation engine
    def __init__(self, root, engine):
        self.root = root
        self.engine = engine

        # Display scaling logic based on screen width
        screen_w = self.root.winfo_screenwidth()
        self.scale = 1.0 if screen_w >= 2000 else 0.75

        # Image cache to prevent reloading files from disk every frame
        self.image_cache = {} 
        # Stores original PIL images for rotation
        self.base_images = {} 

        # Initialize loop identifiers and time tracking
        self.sim_loop_id = None
        self.smooth_loop_id = None
        self.last_tick_real_time = time.time()
        self.pending_runway_removals = []
        self.pending_status_changes = {}
        
        # Tracks whichever widget is currently highlighted
        # Format: {'type': 'plane'|'runway', 'id': str, 'widget': dict_ref}
        self.selection_data = None 
        
        # Initialize report storage
        self.last_saved_report = None
        self.last_saved_time = None

        # Ensure speed multiplier exists on the engine
        if not hasattr(self.engine, 'speed_multiplier'):
            self.engine.speed_multiplier = 1.0

        # Dictionaries to store active widgets
        self.holding_plane_widgets = {}
        self.takeoff_plane_widgets = {}
        self.runway_widgets = {}

        # Run initial setup functions
        self.setup_window()
        self.setup_styles()
        self.bind_keys()
        # Load images once at start
        self.preload_images() 

        # Flag to track if UI has been built
        self.ui_built = False
        # Open settings immediately on launch
        self.open_simulation_settings()

    def preload_images(self):
        assets = [
            "display_plane.png",
            "display_plane_waiting.png",
            "display_plane_on_runway.png",
            "display_runway.png",
            "idle_icon.png",
            "cycle_icon.png",
            "warning_icon.png"
        ]

        for name in assets:
            try:
                path = resource_path(os.path.join("frontend", "assets", name))
                img = Image.open(path).convert("RGBA")
                self.base_images[name] = img
                print(f"Loaded asset: {path}")
            except Exception as e:
                print(f"Warning: Could not load {name} from {path}: {e}")

    # Configure the main window dimensions and colors
    def setup_window(self):
        self.window_w = self.root.winfo_screenwidth() - 100
        self.window_h = self.root.winfo_screenheight() - 100

        # Define margins and gaps
        self.margin_x = self.window_w / 96
        self.margin_y = self.window_h / 54
        self.gap = self.window_w / 120

        # Calculate column widths and heights
        self.col_w_standard = self.window_w * (7/32)
        self.col_w_display = self.window_w * (143/480)
        self.panel_h = int(54 * self.scale)
        self.top_col_h = self.window_h - (2 * self.margin_y) - self.panel_h - self.gap

        # Define color palette
        self.dark_grey = "#2b2b2b"
        self.medium_grey = "#404040"
        self.light_grey = "#5c5c5c"
        self.lightest_grey = "#A6A4A4"
        self.text_color = "#000000"
        self.emergency_text_color = "#5c0000"

        # Configure root window attributes
        self.root.title("Airport Simulation")
        self.root.geometry(f"{int(self.window_w)}x{int(self.window_h)}")
        self.root.configure(bg=self.dark_grey)
        self.root.resizable(False, False)

    # Configure custom styles for widgets
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define common settings for progress bars
        common_bar_settings = {
            "thickness": int(20 * self.scale),
            "troughcolor": "#797979",
            "bordercolor": "#797979",
        }

        # Configure specific progress bar styles
        style.configure("Orange.Horizontal.TProgressbar", foreground="#d18800", background="#d18800", lightcolor="#f0b13b", darkcolor="#613F00", **common_bar_settings)
        style.configure("Green.Horizontal.TProgressbar", foreground="#008000", background="#008000", lightcolor="#37CA37", darkcolor="#005300", **common_bar_settings)
        # Configure scrollbar style
        style.configure("Vertical.TScrollbar", gripcount=0, background=self.lightest_grey, troughcolor=self.medium_grey, bordercolor=self.dark_grey, arrowcolor=self.medium_grey, arrowsize=int(13 * self.scale))
        style.map("Vertical.TScrollbar", background=[("active", "#dcdad5"), ("disabled", self.lightest_grey)], troughcolor=[("active", self.medium_grey), ("disabled", self.medium_grey)])

    # Bind keyboard shortcuts to functions
    def bind_keys(self):
        self.root.bind("P", lambda x: self.toggle_pause())
        self.root.bind("p", lambda x: self.toggle_pause())
        self.root.bind("S", lambda x: self.open_simulation_settings())
        self.root.bind("s", lambda x: self.open_simulation_settings())
        self.root.bind("V", lambda x: self.open_statistics())
        self.root.bind("v", lambda x: self.open_statistics())
        self.root.bind("R", lambda x: self.reset_simulation())
        self.root.bind("r", lambda x: self.reset_simulation())
        self.root.bind("X", lambda x: self.stop_simulation())
        self.root.bind("x", lambda x: self.stop_simulation())

    # Stop the simulation and save the final report
    def stop_simulation(self):
        self.toggle_pause(force_pause=True)
        try:
            # Capture the final state
            self.last_saved_report = self.engine.get_report()
            self.last_saved_time = self.engine.get_time()
            try:
                # Append report to CSV
                append_report_csv(self.last_saved_report or {}, int(self.last_saved_time or 0), DEFAULT_STATS_CSV_PATH)
            except Exception as e:
                print(f"CSV save failed: {e}")
        except Exception:
            self.last_saved_report = None
            self.last_saved_time = None
        # Open statistics window showing saved data
        self.open_statistics(show_saved=True, stop_flow=True)



    # Helper function to create a UI section with optional scrolling
    def create_section(self, parent, x, y, w, h, name, title=True, scrollable=False):
        # Create outer frame for border effect
        outer_frame = tk.Frame(parent, bg=self.medium_grey, width=w, height=h)
        outer_frame.place(x=x, y=y)

        # Calculate inner dimensions
        inset = 4
        inner_w = w - (inset * 2)
        inner_h = h - (inset * 2)
        inner_frame = tk.Frame(outer_frame, bg=self.light_grey, width=inner_w, height=inner_h)
        inner_frame.place(x=inset, y=inset, width=inner_w, height=inner_h)

        title_h = int(40 * self.scale)

        # Add title label if requested
        if title:
            tk.Label(inner_frame, text=name, bg=self.lightest_grey, fg=self.text_color, font=("Arial", int(14 * self.scale), "bold")).place(relx=0, rely=0, relwidth=1, anchor="nw")

        # Return simple frame if scrolling is not needed
        if not scrollable:
            return inner_frame

        # Setup canvas and scrollbar for scrollable sections
        canvas = tk.Canvas(inner_frame, bg=self.light_grey, highlightthickness=0)
        scrollbar = ttk.Scrollbar(inner_frame, orient="vertical", command=canvas.yview)
        scrollable_inner_frame = tk.Frame(canvas, bg=self.light_grey)
        window = canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")

        # Function to handle scrollbar visibility
        def update_scroll_visibility(event=None):
            inner_frame.update_idletasks()
            content_height = scrollable_inner_frame.winfo_reqheight()
            visible_height = canvas.winfo_height()
            if content_height <= visible_height:
                scrollbar.place_forget()
                canvas.yview_moveto(0)
            else:
                scrollbar.place(relx=1, y=title_h, anchor="ne", height=inner_h - title_h)
                canvas.configure(scrollregion=canvas.bbox("all"))

        # Bind configuration events
        scrollable_inner_frame.bind("<Configure>", update_scroll_visibility)
        def resize_scrollable_frame(event):
            canvas.itemconfig(window, width=event.width)
            update_scroll_visibility()
        
        # Mouse wheel scrolling logic
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        # Bind mouse events for scrolling
        inner_frame.bind("<Enter>", _bind_to_mousewheel)
        inner_frame.bind("<Leave>", _unbind_from_mousewheel)
        canvas.bind("<Enter>", _bind_to_mousewheel)
        scrollable_inner_frame.bind("<Enter>", _bind_to_mousewheel)
        canvas.bind("<Configure>", resize_scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.place(x=0, y=title_h, relwidth=1, height=inner_h - title_h)

        return scrollable_inner_frame

    # Construct the main interface layout
    def build_interface(self):
        x_pos = self.margin_x
        # Create takeoff queue section
        self.takeoff_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Take-off Queue", scrollable=True)

        x_pos += self.col_w_standard + self.gap
        # Create holding queue section
        self.holding_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Holding Queue", scrollable=True)

        x_pos += self.col_w_standard + self.gap
        # Create visual display area
        self.display_area_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_display, self.col_w_display, "Display", title=False)

        # Feature: Display Status Overlay
        self.display_status_label = tk.Label(
            self.display_area_frame, 
            text="Nothing Selected", 
            bg="#202020", 
            fg="white", 
            font=("Arial", int(12 * self.scale), "bold"),
            # Add some horizontal padding for the text inside the box
            padx=10, 
            pady=5
        )
        # Hug the top-right (relx=0, rely=0) using the North-West anchor
        self.display_status_label.place(relx=0, rely=0, anchor="nw")
        # We don't pack it yet; we place it in _render_display_image so it stays on top

        y_pos_3_2 = self.margin_y + self.col_w_display + self.gap
        h_3_2 = self.top_col_h - self.col_w_display - self.gap
        # Create info panel
        self.display_info_frame = self.create_section(self.root, x_pos, y_pos_3_2, self.col_w_display, h_3_2, "Nothing Selected")

        x_pos += self.col_w_display + self.gap
        # Create runways section
        self.runway_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Runways", scrollable=True)

        # Create control panel at the bottom
        panel_w = self.window_w - (2 * self.margin_x)
        panel_y = self.window_h - self.margin_y - self.panel_h
        control_panel_frame = self.create_section(self.root, self.margin_x, panel_y, panel_w, self.panel_h, "Control Panel", title=False)
        control_panel_frame.rowconfigure(0, weight=1)

        # Add clock label
        self.clock_label = tk.Label(control_panel_frame, text="00:00", bg=self.lightest_grey, fg=self.text_color, font=("Arial", int(17 * self.scale), "bold"))
        self.clock_label.grid(column=0, row=0, sticky="nsew", padx=[7,5], pady=7, ipadx=5)

        # Add control buttons
        tk.Button(control_panel_frame, text="Pause/Continue [P]", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold", "underline"), padx=5, relief="flat", command=self.toggle_pause).grid(column=1, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="Simulation Settings [S]", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold", "underline"), padx=5, relief="flat", command=self.open_simulation_settings).grid(column=2, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="View Statistics [V]", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold", "underline"), padx=5, relief="flat", command=self.open_statistics).grid(column=3, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="Reset Simulation [R]", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold", "underline"), padx=5, relief="flat", command=self.reset_simulation).grid(column=4, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="Stop [X]", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold", "underline"), padx=5, relief="flat", command=self.stop_simulation).grid(column=5, row=0, sticky="nsew", padx=5, pady=7)

    # --- Popups (Settings & Stats) - Code mostly unchanged but included for completeness ---
    # Open the settings modal window
    def open_simulation_settings(self, event=None):
        # Bring existing window to front if open
        if hasattr(self, 'settings_win') and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
        self.toggle_pause(force_pause=True)
        # Create new toplevel window
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Simulation Settings")
        self.settings_win.geometry(f"{int(500 * self.scale)}x{int(600 * self.scale)}")
        self.settings_win.configure(bg=self.dark_grey)
        self.settings_win.grab_set()
        self.settings_win.resizable(False, False)
        self.settings_win.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # Create main card frame
        main_card = tk.Frame(self.settings_win, bg=self.lightest_grey, relief="flat")
        main_card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95, relheight=0.95)

        header_frame = tk.Frame(main_card, bg=self.lightest_grey)
        header_frame.pack(fill="x", pady=(15, 10))
        tk.Label(header_frame, text="SIMULATION PARAMETERS", font=("Arial", int(14 * self.scale), "bold"), bg=self.lightest_grey, fg=self.text_color).pack()

        # Create container for input rows
        rows_container = tk.Frame(main_card, bg=self.lightest_grey)
        rows_container.pack(fill="both", expand=True, padx=2, pady=2)

        entries = {}
        color_a = self.lightest_grey
        color_b = "#BDBDBD"

        # Helper to add a setting row
        def add_setting(idx, label_text, default_val):
            bg_color = color_a if idx % 2 == 0 else color_b
            row = tk.Frame(rows_container, bg=bg_color)
            row.pack(fill="x")
            tk.Label(row, text=label_text, bg=bg_color, fg=self.text_color, font=("Arial", int(11 * self.scale), "bold")).pack(side="left", padx=20, pady=10 * self.scale)
            entry = ttk.Entry(row, font=("Arial", int(11 * self.scale)), width=8, justify="center")
            entry.insert(0, str(default_val))
            entry.pack(side="right", padx=20, pady=10 * self.scale)
            entries[label_text] = entry

        # Get current parameters or defaults
        p = getattr(self.engine, 'params', None)
        curr_runways = len(self.engine.airport.runways) if hasattr(self.engine, 'airport') else 3
        curr_speed = getattr(self.engine, 'speed_multiplier', 1.0)
        settings_list = [
            ("Number Of Runways:", curr_runways),
            ("Inbound flow (per hour):", getattr(p, 'inbound_rate_per_hour', 10) if p else 10),
            ("Outbound flow (per hour):", getattr(p, 'outbound_rate_per_hour', 10) if p else 10),
            ("Simulation speed multiplier:", curr_speed),
            ("Max take off wait (mins):", getattr(p, 'max_takeoff_wait_min', 30.0) if p else 30.0),
            ("Min fuel levels (mins):", getattr(p, 'fuel_min_min', 10.0) if p else 10.0),
            ("Rate of emergencies:", (getattr(p, 'p_mechanical_failure', 0.0) + getattr(p, 'p_passenger_illness', 0.0)) * 100 if p else 0)
        ]
        # Populate settings
        for i, (label, val) in enumerate(settings_list):
            add_setting(i, label, val)

        error_label = tk.Label(main_card, text="", fg=self.emergency_text_color, bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"))
        error_label.pack(pady=5)

        # Apply settings logic
        def apply():
            try:
                values = {
                    "Number Of Runways:": int(entries["Number Of Runways:"].get()),
                    "Inbound flow (per hour):": float(entries["Inbound flow (per hour):"].get()),
                    "Outbound flow (per hour):": float(entries["Outbound flow (per hour):"].get()),
                    "Simulation speed multiplier:": float(entries["Simulation speed multiplier:"].get()),
                    "Max take off wait (mins):": float(entries["Max take off wait (mins):"].get()),
                    "Min fuel levels (mins):": float(entries["Min fuel levels (mins):"].get()),
                    "Rate of emergencies:": float(entries["Rate of emergencies:"].get()),
                }

                # Restore Validation Rules
                rules = {
                    "Number Of Runways:": (1, 10, False),
                    "Inbound flow (per hour):": (1, 45, False),
                    "Outbound flow (per hour):": (1, 45, False),
                    "Simulation speed multiplier:": (0, 10, True),
                    "Max take off wait (mins):": (20, 59, False),
                    "Min fuel levels (mins):": (10, 30, False),
                    "Rate of emergencies:": (0, 50, True),
                }
                
                for label, (range_min, range_max, exclude_0) in rules.items():
                    v = values[label]
                    if exclude_0 and not (v > range_min and v <= range_max):
                        error_label.config(text=f"Invalid input: '{label}' must be between 0 and {range_max} (not 0)")
                        return
                    elif not exclude_0 and not (range_min <= v <= range_max):
                        error_label.config(text=f"Invalid input: '{label}' must be between {range_min} and {range_max}")
                        return

                self.apply_parameters(
                    values["Number Of Runways:"], values["Inbound flow (per hour):"], values["Outbound flow (per hour):"],
                    values["Simulation speed multiplier:"], values["Max take off wait (mins):"], values["Min fuel levels (mins):"], values["Rate of emergencies:"]
                )

                if not getattr(self, "ui_built", False):
                    self.build_interface()
                    self.ui_built = True

                self.update_ui()
                self.settings_win.destroy()
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.toggle_pause(force_play=True)
            except ValueError:
                error_label.config(text="Invalid input: use numbers only")

        tk.Button(main_card, text="APPLY CHANGES", bg=self.lightest_grey, fg=self.text_color, font=("Arial", int(11 * self.scale), "bold"), relief="solid", borderwidth=1, padx=20, command=apply).pack(pady=(0, 20))

    # Open the statistics modal window
    def open_statistics(self, event=None, show_saved=False, stop_flow=False):
        if hasattr(self, 'stats_win') and self.stats_win.winfo_exists():
            self.stats_win.lift()
            return

        self.toggle_pause(force_pause=True)
        self.stats_win = tk.Toplevel(self.root)
        self.stats_win.title("Statistical Report" if not stop_flow else "Simulation Stopped - Statistics")
        self.stats_win.configure(bg=self.dark_grey)
        self.stats_win.grab_set()

        if stop_flow:
            self.stats_win.protocol("WM_DELETE_WINDOW", self.stats_win.destroy)
        else:
            self.stats_win.protocol("WM_DELETE_WINDOW", lambda: [self.stats_win.destroy(), self.toggle_pause(force_play=True)])

        container = tk.Frame(self.stats_win, bg=self.lightest_grey, padx=20, pady=20)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        header = "Live Statistical Report" if not stop_flow else "Simulation Stopped - Statistics"
        tk.Label(container, text=header, font=("Arial", int(16 * self.scale), "bold"), bg=self.lightest_grey).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        notebook = ttk.Notebook(container)
        notebook.grid(row=1, column=0, columnspan=2, sticky="nsew")
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        def _safe_num(v, default=0):
            try:
                if v is None or (isinstance(v, str) and v.strip() == ""): return default
                fv = float(v)
                return default if fv != fv else fv
            except Exception: return default

        def _render_report(parent, report_data, sim_time_min=None):
            report_data = report_data or {}
            frame = tk.Frame(parent, bg=self.lightest_grey)
            frame.pack(fill="both", expand=True)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_columnconfigure(1, weight=1)

            def add_stat(row, label, val):
                if isinstance(val, (int, float)): val = _safe_num(val, 0)
                display = f"{val:.2f}" if isinstance(val, float) else str(val)
                tk.Label(frame, text=label, bg=self.lightest_grey, font=("Arial", int(11 * self.scale), "bold")).grid(row=row, column=0, sticky="w", pady=2)
                tk.Label(frame, text=display, bg=self.lightest_grey, font=("Arial", int(11 * self.scale))).grid(row=row, column=1, sticky="e", pady=2)

            add_stat(0, "Max holding queue size:", report_data.get("maxHoldingQueue", 0))
            add_stat(1, "Avg holding queue size:", report_data.get("avgHoldingQueue", 0))
            add_stat(2, "Max holding queue wait time (m):", report_data.get("maxArrivalDelay", 0))
            add_stat(3, "Avg holding queue wait time (m):", report_data.get("avgHoldingTime", 0))
            add_stat(4, "Max take off queue size:", report_data.get("maxTakeoffQueue", 0))
            add_stat(5, "Avg take off queue size:", report_data.get("avgTakeoffQueue", 0))
            add_stat(6, "Max take off queue wait time (m):", report_data.get("maxTakeoffWait", 0))
            add_stat(7, "Avg take off queue wait time (m):", report_data.get("avgTakeoffWait", 0))
            add_stat(8, "Total inbound diversions:", report_data.get("diversions", 0))
            add_stat(9, "Total outbound cancellations:", report_data.get("cancellations", 0))

            if sim_time_min is None: sim_time_min = report_data.get("sim_time_min", self.engine.get_time())
            add_stat(10, "Total simulation time:", self.format_time(int(_safe_num(sim_time_min, 0))))

            if isinstance(report_data, dict) and report_data.get("saved_at_utc"):
                tk.Label(frame, text=f"Saved at (UTC): {report_data.get('saved_at_utc')}", bg=self.lightest_grey, font=("Arial", int(9 * self.scale))).grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Handle Current Tab data
        if stop_flow or show_saved:
            try:
                current_report = dict(read_last_report(DEFAULT_STATS_CSV_PATH) or {})
            except Exception:
                current_report = dict(self.last_saved_report) if self.last_saved_report is not None else {}
            current_time = current_report.get("sim_time_min", self.last_saved_time if self.last_saved_time is not None else self.engine.get_time())
        else:
            current_report = self.engine.get_report()
            current_time = self.engine.get_time()

        current_tab = tk.Frame(notebook, bg=self.lightest_grey)
        notebook.add(current_tab, text="Current")
        _render_report(current_tab, current_report, current_time)

        # Handle CSV reading for Previous Runs
        def _read_all_reports_csv(path):
            import csv
            rows = []
            try:
                with open(path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader: rows.append(dict(r))
            except Exception: return []
            return rows

        previous_runs = _read_all_reports_csv(DEFAULT_STATS_CSV_PATH)
        if previous_runs and previous_runs[0].get("saved_at_utc"):
            previous_runs.sort(key=lambda r: (r.get("saved_at_utc") or ""), reverse=True)

        for idx, run in enumerate(previous_runs[:12], start=1):
            sim_t = int(_safe_num(run.get("sim_time_min", 0), 0))
            tab = tk.Frame(notebook, bg=self.lightest_grey)
            notebook.add(tab, text=f"Run {idx} ({self.format_time(sim_t)})")
            _render_report(tab, run, sim_t)

        # Buttons at bottom
        if stop_flow:
            tk.Button(container, text="Close", bg=self.medium_grey, fg="white", font=("Arial", int(12 * self.scale), "bold"), command=self.stats_win.destroy).grid(row=2, column=0, pady=20, ipadx=20, sticky="ew")
            def _reset():
                self.stats_win.destroy()
                self.reset_simulation(open_settings=True)
            tk.Button(container, text="Reset Simulation", bg=self.medium_grey, fg="white", font=("Arial", int(12 * self.scale), "bold"), command=_reset).grid(row=2, column=1, pady=20, ipadx=20, sticky="ew")
        else:
            tk.Button(container, text="Close", bg=self.medium_grey, fg="white", font=("Arial", int(12 * self.scale), "bold"), command=lambda: [self.stats_win.destroy(), self.toggle_pause(force_play=True)]).grid(row=2, column=0, columnspan=2, pady=20, ipadx=20)

        self.stats_win.update_idletasks()
        req_h = self.stats_win.winfo_reqheight()
        fixed_w = int(500 * self.scale)
        x = int((self.root.winfo_screenwidth() - fixed_w) / 2)
        y = int((self.root.winfo_screenheight() - req_h) / 2)
        self.stats_win.geometry(f"{fixed_w}x{req_h}+{x}+{y}")

    # --- Data Application ---

    # Apply new parameters to the simulation engine
    def apply_parameters(self, num_runways, in_flow, out_flow, speed_mult, max_wait, min_fuel, emerg_rate):
        params = SimulationParams(
            num_runways=num_runways, inbound_rate_per_hour=in_flow, outbound_rate_per_hour=out_flow,
            max_takeoff_wait_min=int(max_wait), arrival_stddev_min=5, departure_stddev_min=5, tick_size_min=1,
            p_mechanical_failure=(emerg_rate / 100.0) / 2, p_passenger_illness=(emerg_rate / 100.0) / 2,
            fuel_emergency_min=15, fuel_min_min=int(min_fuel)
        )
        self.engine.speed_multiplier = speed_mult
        self.engine.params = params
        self.engine.stats.configure_from_params(params)
        self.engine.regenerate_schedule(lookahead_window=15)

        # Adjust runway count dynamically
        current_runways = list(self.engine.airport.runways)
        if num_runways > len(current_runways):
            highest_id = max([r.id for r in current_runways]) if current_runways else 0
            for i in range(num_runways - len(current_runways)):
                highest_id += 1
                current_runways.append(Runway(runway_id=highest_id, runway_mode="MIXED"))
            self.engine.airport.runways = current_runways
        elif num_runways < len(current_runways):
            # Mark runways for closure if reducing count
            for r in current_runways[num_runways:]:
                if r not in self.pending_runway_removals:
                    self.pending_runway_removals.append(r)
                    r.status = "Closed"
            self.engine.airport.runways = current_runways

        # Refresh UI if it is already built
        if getattr(self, "ui_built", False):
            self.update_ui()

    # --- Core Simulation Loop ---

    # Toggle simulation pause state
    def toggle_pause(self, force_pause=False, force_play=False):
        if force_pause: self.engine.is_paused = True
        elif force_play: self.engine.is_paused = False
        else: self.engine.is_paused = not self.engine.is_paused

        if self.engine.is_paused:
            if self.sim_loop_id:
                self.root.after_cancel(self.sim_loop_id)
                self.sim_loop_id = None
            if self.smooth_loop_id:
                self.root.after_cancel(self.smooth_loop_id)
                self.smooth_loop_id = None
        else:
            self.last_tick_real_time = time.time()
            self.simulation_tick()
            self.smooth_update()

    # Reset the simulation to initial state
    def reset_simulation(self, open_settings=True):
        self.toggle_pause(force_pause=True)
        self.engine.current_time = 0
        
        # Reset statistics
        new_stats = Statistics()
        new_stats.configure_from_params(self.engine.params)
        self.engine.stats = new_stats
        self.engine.airport.stats = new_stats
        
        # Reset queues and accumulators
        self.engine.airport.holding = HoldingQueue()
        self.engine.airport.takeoff = TakeOffQueue()
        self.engine._pending_inbound.clear()
        self.engine._pending_outbound.clear()
        self.pending_status_changes.clear()
        self.pending_runway_removals.clear()
        self.engine._inbound_acc = 0.0
        self.engine._outbound_acc = 0.0
        self.engine._next_in_id = 1
        self.engine._next_out_id = 1
        self.engine._prime_scheduler(lookahead_window=15)

        # Reset runways
        for runway in self.engine.airport.runways:
            runway.currentAircraft = None
            runway.currentOperation = None
            runway.status = "AVAILABLE"
            runway.occupancy = "FREE"
            runway.startTime = 0
            runway.duration = 0

        # Clear UI elements
        self.pending_runway_removals.clear()
        for w in list(self.holding_plane_widgets.values()): w["frame"].destroy()
        self.holding_plane_widgets.clear()
        for w in list(self.takeoff_plane_widgets.values()): w["frame"].destroy()
        self.takeoff_plane_widgets.clear()
        for w in list(self.runway_widgets.values()): w["frame"].destroy()
        self.runway_widgets.clear()

        # Reset selection
        self.selection_data = None
        self.show_idle_display()

        self.update_ui()
        if open_settings:
            self.open_simulation_settings()
        else:
            self.toggle_pause(force_play=True)

    def clear_info_panel(self):
        for w in list(self.display_info_frame.winfo_children()):
            w.destroy()
        tk.Label(self.display_info_frame, text="Nothing Selected", bg=self.lightest_grey, fg=self.text_color, font=("Arial", int(14 * self.scale), "bold")).place(relx=0, rely=0, relwidth=1, anchor="nw")
        
    # Main simulation tick function
    def simulation_tick(self):
        if self.engine.is_paused: return
        self.engine.tick()
        self.last_tick_real_time = time.time()

        # Handle pending runway removals
        for r in self.pending_runway_removals[:]:
            if r.currentAircraft is None or r.occupancy == "FREE":
                current_list = list(self.engine.airport.runways)
                if r in current_list:
                    current_list.remove(r)
                    self.engine.airport.runways = current_list
                self.pending_runway_removals.remove(r)
        
        # Handle pending status changes
        for r in list(self.pending_status_changes):
            if r.currentAircraft is None:
                next_status, wf, pc, pgs = self.pending_status_changes.pop(r)
                r.status = next_status
                self._apply_status_visuals(next_status, wf, pc, pgs)

        self.update_ui()

        # Fix: Update Display Area if Selection Changes State
        if self.selection_data:
            sel_type = self.selection_data['type']
            sel_id = self.selection_data['id']
            
            should_reset = False
            
            if sel_type == 'plane':
                # Find plane object
                all_objs = self.engine.get_holding_queue() + self.engine.get_takeoff_queue()
                for r in self.engine.get_runways():
                    if r.currentAircraft: all_objs.append(r.currentAircraft)
                
                plane = next((p for p in all_objs if p.callsign == sel_id), None)
                
                if plane:
                    # Plane still exists, refresh display
                    self.show_aircraft_in_display(plane)
                else:
                    # Plane deleted/departed
                    should_reset = True
            
            elif sel_type == 'runway':
                # Find runway object
                # Note: Runways are integers, sel_id is likely string
                rw = next((r for r in self.engine.get_runways() if str(r.id) == str(sel_id)), None)
                
                if rw:
                    self.show_runway_in_display(rw)
                else:
                    should_reset = True

            if should_reset:
                self.selection_data = None
                self.show_idle_display()
                self.clear_info_panel()

        speed = float(getattr(self.engine, 'speed_multiplier', 1.0))
        interval = int(1000 / speed) if speed > 0 else 1000
        self.sim_loop_id = self.root.after(interval, self.simulation_tick)

    # Smooth progress bar updates between ticks
    def smooth_update(self):
        if self.engine.is_paused: return
        try:
            speed = float(getattr(self.engine, 'speed_multiplier', 1.0))
            tick_duration_ms = 1000 / speed if speed > 0 else 1000
            real_time_passed = (time.time() - self.last_tick_real_time) * 1000
            tick_fraction = min(1.0, real_time_passed / tick_duration_ms)

            active_aircraft_data = {}
            # Update runway progress bars
            for r in self.engine.get_runways():
                if r.currentAircraft and r.occupancy == "OCCUPIED":
                    active_aircraft_data[r.currentAircraft.callsign] = {
                        "start": r.startTime, "duration": getattr(r, 'duration', 1)
                    }
                    if r.id in self.runway_widgets:
                        w = self.runway_widgets[r.id]
                        elapsed = self.engine.get_time() - r.startTime
                        smooth_val = ((elapsed + tick_fraction) / max(getattr(r, 'duration', 1), 1)) * 100
                        if w["progress"]["value"] != smooth_val:
                            w["progress"]["value"] = min(100, smooth_val)
                else:
                    if r.id in self.runway_widgets and self.runway_widgets[r.id]["progress"]["value"] != 0:
                        self.runway_widgets[r.id]["progress"]["value"] = 0

            # Update queue progress bars
            for cs, widget in itertools.chain(self.holding_plane_widgets.items(), self.takeoff_plane_widgets.items()):
                if cs in active_aircraft_data:
                    data = active_aircraft_data[cs]
                    elapsed = self.engine.get_time() - data["start"]
                    smooth_val = ((elapsed + tick_fraction) / max(data["duration"], 1)) * 100
                    if widget["progress"]["value"] != smooth_val:
                        widget["progress"]["value"] = min(100, smooth_val)
                else:
                    if widget["progress"]["value"] != 0:
                        widget["progress"]["value"] = 0
        except Exception:
            pass 
        self.smooth_loop_id = self.root.after(16, self.smooth_update)

    # Refresh the entire UI state
    def update_ui(self):
        all_runways = self.engine.get_runways()
        active_inbound = [r.currentAircraft for r in all_runways if r.currentAircraft and r.currentAircraft.type == "INBOUND"]
        full_holding_list = active_inbound + self.engine.get_holding_queue()
        active_outbound = [r.currentAircraft for r in all_runways if r.currentAircraft and r.currentAircraft.type == "OUTBOUND"]
        full_takeoff_list = active_outbound + self.engine.get_takeoff_queue()
        
        self.update_plane_queue(full_holding_list[:50], self.holding_queue_frame, self.holding_plane_widgets)
        self.update_plane_queue(full_takeoff_list[:50], self.takeoff_queue_frame, self.takeoff_plane_widgets)
        self.update_runway_queue(all_runways, self.runway_queue_frame, self.runway_widgets)
        self.clock_label.config(text=f"{self.format_time(self.engine.get_time())}")

    # Format simulation time as HH:MM
    def format_time(self, time_var):
        hours = (time_var // 60) % 24
        minutes = time_var % 60
        return f"{hours:02d}:{minutes:02d}"

    # Update widgets for plane queues
    def update_plane_queue(self, queue, frame, widget_dict):
        current_ids = set()
        for plane in queue:
            pid = plane.callsign
            current_ids.add(pid)
            if pid not in widget_dict:
                widget_dict[pid] = self.create_plane_widget(frame, plane)
            self.update_plane_widget(widget_dict[pid], plane)

        # Improvement: Safe deletion (Iterate over copy of keys)
        for pid in list(widget_dict.keys()):
            if pid not in current_ids:
                if self.selection_data and self.selection_data['id'] == pid:
                    self.selection_data = None
                    self.show_idle_display()
                    self.clear_info_panel()
                widget_dict[pid]["frame"].destroy()
                del widget_dict[pid]

    # Create a new widget representing a plane
    def create_plane_widget(self, queue_column, plane):
        widget_frame = tk.Frame(queue_column, bg=self.lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)

        tl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", int(13 * self.scale), "bold"), anchor="w")
        tr = tk.Label(widget_frame, text="", bg=self.lightest_grey, fg=self.emergency_text_color, font=("Arial", int(11 * self.scale), "bold"), anchor="e")
        ml = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", int(11 * self.scale)), anchor="w")
        mr = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", max(4, int(5 * self.scale))), anchor="e")
        bl = tk.Label(widget_frame, text="[Progress]", bg=self.lightest_grey, font=("Arial", int(11 * self.scale), "bold"), anchor="w")
        br = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", int(11 * self.scale)), anchor="e")

        tl.grid(row=0, column=0, sticky="w")
        tr.grid(row=0, column=1, sticky="e")
        ml.grid(row=1, column=0, sticky="w")
        mr.grid(row=1, column=1, sticky="e")
        bl.grid(row=2, column=0, sticky="w")
        br.grid(row=2, column=1, sticky="e")

        pc = tk.Frame(widget_frame, height=int(13 * self.scale), bg=self.lightest_grey)
        pc.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        pc.pack_propagate(False)
        progress = ttk.Progressbar(pc, orient="horizontal", mode="determinate")
        progress.pack(fill="both", expand=True)

        widget_ref = { "frame": widget_frame, "tl": tl, "tr": tr, "ml": ml, "bl": bl, "br": br, "progress": progress }
        
        # Click handler for selection
        def on_click(e):
            self.select_widget(widget_ref, 'plane', plane.callsign)
            self.show_airplane_info(plane)
            self.show_aircraft_in_display(plane)

        widget_frame.bind("<Button-1>", on_click)
        for lbl in (tl, tr, ml, mr, bl, br): lbl.bind("<Button-1>", on_click)
        return widget_ref

    # Update data displayed on a plane widget
    def update_plane_widget(self, widget, plane):
        emerg = ""
        if hasattr(plane, 'emergency') and plane.emergency:
            if plane.emergency.mechanical_failure: emerg = "Mechanical Failure"
            elif plane.emergency.passenger_illness: emerg = "Passenger Illness"
            elif plane.emergency.fuel_emergency: emerg = "Fuel Emergency"

        if widget["tl"].cget("text") != plane.callsign: widget["tl"].config(text=plane.callsign)
        if widget["tr"].cget("text") != emerg: widget["tr"].config(text=emerg)
        if widget["ml"].cget("text") != getattr(plane, 'operator', 'Unknown'): widget["ml"].config(text=getattr(plane, 'operator', 'Unknown'))
        
        sched = "Scheduled " + self.format_time(getattr(plane, 'scheduledTime', 0))
        if widget["br"].cget("text") != sched: widget["br"].config(text=sched)

        active_runway = next((r for r in self.engine.get_runways() if r.currentAircraft == plane), None)
        status_text = ""
        status_color = self.text_color

        if active_runway:
            action = "Landing" if plane.type == "INBOUND" else "Taking Off"
            status_text = f"{action} - Runway {active_runway.id}"
        else:
            current_time = self.engine.get_time()
            if plane.type == "INBOUND":
                fuel = getattr(plane, 'fuelRemaining', 0)
                status_text = f"Fuel remaining: {fuel}min"
                if fuel <= (getattr(self.engine.params, 'fuel_min_min', 10) + 5):
                    status_color = self.emergency_text_color
            else:
                wait_time = int(current_time - (plane.joinedTakeoffQueueAt if hasattr(plane, 'joinedTakeoffQueueAt') else getattr(plane, 'scheduledTime', 0)))
                status_text = f"Waiting for {wait_time}min"
                if wait_time >= (getattr(self.engine.params, 'max_takeoff_wait_min', 30) - 5):
                    status_color = self.emergency_text_color

        if widget["bl"].cget("text") != status_text: widget["bl"].config(text=status_text)
        if widget["bl"].cget("fg") != status_color: widget["bl"].config(fg=status_color)

        style = "Orange.Horizontal.TProgressbar" if plane.type == "INBOUND" else "Green.Horizontal.TProgressbar"
        if widget["progress"].cget("style") != style: widget["progress"].config(style=style)

    # Update widgets for runway list
    def update_runway_queue(self, queue, frame, widget_dict):
        current_ids = set()
        for rw in queue:
            rid = rw.id
            current_ids.add(rid)
            if rid not in widget_dict:
                widget_dict[rid] = self.create_runway_widget(frame, rw)
            self.update_runway_widget(widget_dict[rid], rw)
        
        # Improvement: Safe deletion
        for rid in list(widget_dict.keys()):
            if rid not in current_ids:
                widget_dict[rid]["frame"].destroy()
                if self.selection_data and self.selection_data['id'] == rid:
                    self.selection_data = None
                    self.show_idle_display()
                del widget_dict[rid]

    # Create a new widget representing a runway
    def create_runway_widget(self, queue_col, rw):
        widget_frame = tk.Frame(queue_col, bg=self.lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)

        pc = tk.Frame(widget_frame, height=int(13 * self.scale), bg=self.lightest_grey)
        pc.pack_propagate(False)
        pg_settings = {"row": 3, "column": 0, "columnspan": 2, "sticky": "ew", "pady": (5, 0)}
        pc.grid(**pg_settings)
        progress = ttk.Progressbar(pc, orient="horizontal", mode="determinate")
        progress.pack(fill="both", expand=True)

        bf = tk.Frame(widget_frame, bg=self.lightest_grey)
        bf.grid(row=0, column=1, sticky="ne")

        # Create button images (small size for buttons)
        btn_size = int(20 * self.scale)

        cycle_img = self.base_images["cycle_icon.png"].resize((btn_size, btn_size), Image.BICUBIC)
        cycle_photo = ImageTk.PhotoImage(cycle_img)

        warning_img = self.base_images["warning_icon.png"].resize((btn_size, btn_size), Image.BICUBIC)
        warning_photo = ImageTk.PhotoImage(warning_img)

        mode_btn = tk.Button(bf, image=cycle_photo, bg=self.lightest_grey, padx=5, relief="solid", command=lambda: self.cycle_runway_mode(rw))
        mode_btn.image = cycle_photo 
        mode_btn.pack(side="right", padx=(2, 0))

        status_btn = tk.Button(bf, image=warning_photo, bg=self.lightest_grey, padx=5, relief="solid", command=lambda r=rw, wf=widget_frame, c=pc: self.cycle_runway_status(r, wf, c, pg_settings))
        status_btn.image = warning_photo
        status_btn.pack(side="right", padx=(0, 2))

        tl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", int(12 * self.scale), "bold"), anchor="w")
        bl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"), anchor="w")
        tl.grid(row=0, column=0, sticky="w")
        bl.grid(row=2, column=0, sticky="w")
        br = tk.Label(widget_frame, text="Status", bg=self.lightest_grey, fg=self.emergency_text_color, font=("Arial", int(9 * self.scale), "bold"), anchor="e")
        br.grid(row=2, column=1, sticky="e")

        widget_ref = { "frame": widget_frame, "tl": tl, "bl": bl, "br": br, "progress": progress }

        def on_click(e):
            if rw.status == "AVAILABLE":
                self.select_widget(widget_ref, 'runway', rw.id)
            self.show_runway_info(rw)
            self.show_runway_in_display(rw)

        widget_frame.bind("<Button-1>", on_click)
        for lbl in (tl, bl, br): lbl.bind("<Button-1>", on_click)
        return widget_ref

    # Update data displayed on a runway widget
    def update_runway_widget(self, widget, rw):
        title = f"Runway {rw.id} - " + ("Landing Only" if rw.mode == "LANDING" else "Take Off Only" if rw.mode == "TAKEOFF" else "Mixed Use")
        if rw in self.pending_runway_removals: title += " (CLOSING)"
        if self.pending_status_changes.get(rw): title += " (Clearing)"

        if rw.currentAircraft is None: airplane_txt = "Not currently in use"
        else:
            dir = "Landing" if rw.currentAircraft.type == "INBOUND" else "Taking Off"
            airplane_txt = f"{rw.currentAircraft.callsign} - {dir}"

        widget["tl"].config(text=title)
        widget["bl"].config(text=airplane_txt)
        widget["br"].config(text="" if rw.status == "AVAILABLE" else rw.status)
        
        style = "Orange.Horizontal.TProgressbar" if getattr(rw, 'currentOperation', '') == "LANDING" else "Green.Horizontal.TProgressbar"
        widget["progress"].config(style=style)

    # Cycle through runway modes (Landing/Takeoff/Mixed)
    def cycle_runway_mode(self, rw):
        if rw in self.pending_runway_removals: return
        rw.mode = "MIXED" if rw.mode == "LANDING" else "TAKEOFF" if rw.mode == "MIXED" else "LANDING"
        self.update_ui()

    # Recursively update background colors for a widget tree
    def update_widget_colors(self, widget, color):
        if not isinstance(widget, (ttk.Progressbar, tk.Button)):
            widget.configure(bg=color)
        for child in widget.winfo_children(): self.update_widget_colors(child, color)

    # Update visual styles based on runway status
    def _apply_status_visuals(self, new_status, wf, pc, pgs):
        if new_status == "AVAILABLE":
            bg, rel, bord, show_prog = self.lightest_grey, "flat", 0, True
        else:
            bg, rel, bord, show_prog = self.light_grey, "solid", 1, False
        wf.config(bg=bg, relief=rel, borderwidth=bord)
        self.update_widget_colors(wf, bg)
        if show_prog: pc.grid(**pgs)
        else: pc.grid_forget()

    # Cycle runway status between Available and Closed
    def cycle_runway_status(self, rw, wf, pc, pgs):
        if rw in self.pending_runway_removals: return
        status_order = ["AVAILABLE", "Closed"]
        pending = self.pending_status_changes.get(rw)
        current = pending[0] if pending else rw.status
        next_status = status_order[(status_order.index(current) + 1) % len(status_order)]

        if rw.currentAircraft is None:
            rw.status = next_status
            self.pending_status_changes.pop(rw, None)
            self._apply_status_visuals(next_status, wf, pc, pgs)
        else:
            rw.status = next_status
            self.pending_status_changes[rw] = (next_status, wf, pc, pgs)
        self.update_ui()

    # --- Info Displays (Modified for Caching & Status Bar) ---

    # Render an image to the display area with rotation and status text
    def _render_display_image(self, image_name, rotation=0, status_text=""):
        # Use Cached Images
        if image_name in self.base_images:
            img = self.base_images[image_name]
            if rotation != 0:
                img = img.rotate(rotation, expand=False)
            
            # Resize
            size = int(self.col_w_display * 1.4)
            img = img.resize((size, size), resample=Image.BICUBIC)
            photo = ImageTk.PhotoImage(img)

            # Update display frame
            for w in self.display_area_frame.winfo_children():
                # Don't delete the status label
                if w != self.display_status_label:
                    w.destroy()

            lbl = tk.Label(self.display_area_frame, image=photo, bg=self.display_area_frame.cget("bg"))
            lbl.image = photo # Keep ref
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            
            # Update Status Label text
            try:
                self.display_status_label.config(text=status_text)
            except tk.TclError:
                # Recreate if destroyed
                self.display_status_label = tk.Label(
                    self.display_area_frame, 
                    text=status_text, 
                    bg="#202020", 
                    fg="white", 
                    font=("Arial", int(12 * self.scale), "bold"),
                    padx=10,
                    pady=5
                )

            # Updated placement for bottom-left hug
            self.display_status_label.place(relx=0, rely=0, anchor="nw")
            self.display_status_label.lift()
        else:
            print(f"Image not found in cache: {image_name}")

    # Determine which image to show for a selected aircraft
    def show_aircraft_in_display(self, plane):
        assigned_runway = next((r for r in self.engine.get_runways() if r.currentAircraft == plane), None)
        
        status_text = ""
        
        if assigned_runway:
            # Plane is on a runway -> Show combined image
            rotation = -assigned_runway.bearing * 10
            action = "Landing" if plane.type == "INBOUND" else "Taking Off"
            status_text = f"Flight {plane.callsign} - {action}"
            self._render_display_image("display_plane_on_runway.png", rotation, status_text)
        else:
            # Plane is in queue -> Determine if Sky or Ground
            if plane.type == "OUTBOUND":
                # Waiting on ground
                current_time = self.engine.get_time()
                wait_time = int(current_time - (plane.joinedTakeoffQueueAt if hasattr(plane, 'joinedTakeoffQueueAt') else getattr(plane, 'scheduledTime', 0)))
                status_text = f"Flight {plane.callsign} - Waiting for {wait_time}min"
                # Use new image for ground queue
                self._render_display_image("display_plane_waiting.png", rotation=0, status_text=status_text)
            else:
                # Holding in sky
                fuel = getattr(plane, 'fuelRemaining', 0)
                status_text = f"Flight {plane.callsign} - Holding (Fuel: {fuel}m)"
                self._render_display_image("display_plane.png", rotation=0, status_text=status_text)

    # Determine which image to show for a selected runway
    def show_runway_in_display(self, runway):
        rotation = -runway.bearing * 10
        status_text = f"Runway {runway.id}"
        
        if runway.currentAircraft:
            # Runway is occupied
            dir = "Landing" if runway.currentAircraft.type == "INBOUND" else "Taking Off"
            status_text += f" - {runway.currentAircraft.callsign} ({dir})"
            self._render_display_image("display_plane_on_runway.png", rotation, status_text)
        else:
            # Runway is empty
            self._render_display_image("display_runway.png", rotation, status_text)

    # Show the default idle screen when nothing is selected
    def show_idle_display(self):
        # Clear everything except the status label
        for w in self.display_area_frame.winfo_children():
            if w != self.display_status_label:
                w.destroy()

        if "idle_icon.png" in self.base_images:
            img = self.base_images["idle_icon.png"]
            img = img.resize((int(self.col_w_display * 1.4), int(self.col_w_display * 1.4)), Image.BICUBIC)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(self.display_area_frame, image=photo, bg=self.light_grey)
            lbl.image = photo 
            lbl.pack(expand=False)
            
        # Reset the status label text since we are idle
        self.display_status_label.config(text="Nothing Selected")
        # Keep the placement consistent even when empty
        self.display_status_label.place(relx=0, rely=0, anchor="nw")
        self.display_status_label.lift()

    # Populate the info panel with aircraft details
    def show_airplane_info(self, airplane):
        for w in self.display_info_frame.winfo_children(): w.destroy()
        tk.Label(self.display_info_frame, text=f"Aircraft {airplane.callsign}", bg=self.lightest_grey, font=("Arial", int(14 * self.scale), "bold")).place(x=0, y=0, relwidth=1)
        f = tk.Frame(self.display_info_frame, bg=self.lightest_grey)
        f.place(x=0, y=int(30 * self.scale), relwidth=1, relheight=1)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        def add(r, l, v):
            tk.Label(f, text=l, bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=10, pady=2)
            tk.Label(f, text=str(v), bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"), anchor="e").grid(row=r, column=1, sticky="e", padx=10, pady=2)
        add(0, "Operator:", getattr(airplane, 'operator', 'N/A'))
        add(1, "Origin:", getattr(airplane, 'origin', 'N/A'))
        add(2, "Destination:", getattr(airplane, 'destination', 'N/A'))
        add(3, "Fuel Level:", getattr(airplane, 'fuelRemaining', 'N/A'))
        add(4, "Altitude:", getattr(airplane, 'altitude', 'N/A'))
        add(5, "Ground Speed:", getattr(airplane, 'ground_speed', 'N/A'))
        add(6, "Scheduled:", self.format_time(getattr(airplane, 'scheduledTime', 0)))

    # Populate the info panel with runway details
    def show_runway_info(self, rw):
        for w in self.display_info_frame.winfo_children(): w.destroy()
        tk.Label(self.display_info_frame, text=f"Runway {rw.id}", bg=self.lightest_grey, font=("Arial", int(14 * self.scale), "bold")).place(x=0, y=0, relwidth=1)
        f = tk.Frame(self.display_info_frame, bg=self.lightest_grey)
        f.place(x=0, y=int(30 * self.scale), relwidth=1, relheight=1)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        def add(r, l, v):
            tk.Label(f, text=l, bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=10, pady=2)
            tk.Label(f, text=str(v), bg=self.lightest_grey, font=("Arial", int(10 * self.scale), "bold"), anchor="e").grid(row=r, column=1, sticky="e", padx=10, pady=2)
        add(0, "Operating Mode:", rw.mode)
        add(1, "Occupancy:", rw.occupancy)
        add(2, "Status:", rw.status)
        add(3, "Length:", f"{getattr(rw, 'length', 'N/A')} m")
        add(4, "Bearing:", rw.getBearingString() if hasattr(rw, 'getBearingString') else "N/A")

    # Highlight a widget visually to indicate selection
    def select_widget(self, widget, type_str, id_str):
        if self.selection_data:
            try:
                self.update_widget_colors(self.selection_data["widget"]["frame"], self.lightest_grey)
            except tk.TclError:
                pass
        self.selection_data = {'type': type_str, 'id': id_str, 'widget': widget}
        self.update_widget_colors(widget["frame"], "#c8c6c6")

# Entry point to launch the UI
def create_ui(engine):
    root = tk.Tk()
    root.withdraw()
    app = AirportUI(root, engine)
    root.mainloop()