# things still TODO:
# Angelina:
# reset simulation 
# time

import tkinter as tk
import time
from tkinter import ttk
from backend.SimulationParameters import SimulationParams
from backend.SimulationEngine import SimulationEngine, EmergencyType
from backend.statistics import Statistics
from backend.queues import HoldingQueue, TakeOffQueue
from backend.runway import Runway
from backend.airport import Airport
from backend.aircraft import Aircraft

class AirportUI:
    def __init__(self, root, engine):
        self.root = root
        self.engine = engine
        
        # Tracks the scheduled after() IDs so we can cancel them on pause.
        self.sim_loop_id = None
        self.smooth_loop_id = None
        # Records real-world time of the last tick for smooth interpolation.
        self.last_tick_real_time = time.time()
        # Runways queued to be removed once they finish their current operation.
        self.pending_runway_removals = []
        # Maps runway -> new status string, applied once the runway clears.
        self.pending_status_changes = {}
        # Keeps track of whichever plane/runway widget is currently highlighted.
        self.selected_widget = None
        
        # Speed multiplier lives on the engine rather than in the frozen SimulationParams.
        if not hasattr(self.engine, 'speed_multiplier'):
            self.engine.speed_multiplier = 1.0
        
        # Dictionaries that map IDs to their corresponding UI widget bundles.
        self.holding_plane_widgets = {}
        self.takeoff_plane_widgets = {}
        self.runway_widgets = {}
        
        self.setup_window()
        self.setup_styles()
        self.build_interface()
        self.bind_keys()
        
        # Open the settings dialog immediately so the user can configure before starting.
        self.open_simulation_settings()
        
    def setup_window(self):
        # Use nearly the full screen, leaving a small border on each side.
        self.window_w = self.root.winfo_screenwidth() - 100
        self.window_h = self.root.winfo_screenheight() - 100

        # Margins and gaps are proportional to the window size so layouts scale.
        self.margin_x = self.window_w / 96
        self.margin_y = self.window_h / 54
        self.gap = self.window_w / 120
        
        # The two standard columns (queues) are narrower than the central display column.
        self.col_w_standard = self.window_w * (7/32)
        self.col_w_display = self.window_w * (143/480)
        # Fixed height for the bottom control panel strip.
        self.panel_h = 54
        # Top columns fill whatever vertical space remains after the panel.
        self.top_col_h = self.window_h - (2 * self.margin_y) - self.panel_h - self.gap
        
        # Colour palette used throughout the UI.
        self.dark_grey = "#2b2b2b"
        self.medium_grey = "#404040"
        self.light_grey = "#5c5c5c"
        self.lightest_grey = "#A6A4A4"
        self.text_color = "#000000"
        self.emergency_text_color = "#5c0000"  # Dark red used to flag emergencies.
        
        self.root.title("Airport Simulation")
        self.root.geometry(f"{int(self.window_w)}x{int(self.window_h)}")
        self.root.configure(bg=self.dark_grey)
        self.root.resizable(False, False)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # Clam gives us the most control over colours.

        # Shared settings applied to every progress bar style.
        common_bar_settings = {
            "thickness": 20,
            "troughcolor": "#797979", 
            "bordercolor": "#797979",
        }

        # Orange bars are used for inbound (landing) aircraft.
        style.configure("Orange.Horizontal.TProgressbar", foreground="#d18800", background="#d18800", lightcolor="#f0b13b", darkcolor="#613F00", **common_bar_settings)
        # Green bars are used for outbound (take-off) aircraft.
        style.configure("Green.Horizontal.TProgressbar", foreground="#008000", background="#008000", lightcolor="#37CA37", darkcolor="#005300", **common_bar_settings)
        # Custom scrollbar styling to match the dark theme.
        style.configure("Vertical.TScrollbar", gripcount=0, background=self.lightest_grey, troughcolor=self.medium_grey, bordercolor=self.dark_grey, arrowcolor=self.medium_grey, arrowsize=13)
        style.map("Vertical.TScrollbar", background=[("active", "#dcdad5"), ("disabled", self.lightest_grey)], troughcolor=[("active", self.medium_grey), ("disabled", self.medium_grey)])

    def bind_keys(self):
        # Both upper and lower case are bound so caps lock state doesn't matter.
        self.root.bind("P", lambda x: self.toggle_pause())
        self.root.bind("p", lambda x: self.toggle_pause())
        self.root.bind("S", lambda x: self.open_simulation_settings())
        self.root.bind("s", lambda x: self.open_simulation_settings())
        self.root.bind("V", lambda x: self.open_statistics())
        self.root.bind("v", lambda x: self.open_statistics())
        self.root.bind("R", lambda x: self.reset_simulation())
        self.root.bind("r", lambda x: self.reset_simulation())

    # --- UI Builders ---

    def create_section(self, parent, x, y, w, h, name, title=True, scrollable=False):
        # Outer frame provides the medium-grey border effect.
        outer_frame = tk.Frame(parent, bg=self.medium_grey, width=w, height=h)
        outer_frame.place(x=x, y=y)
        
        # Inner frame sits 4 px inside the outer, giving the illusion of a border.
        inset = 4
        inner_w = w - (inset * 2)
        inner_h = h - (inset * 2)
        inner_frame = tk.Frame(outer_frame, bg=self.light_grey, width=inner_w, height=inner_h)
        inner_frame.place(x=inset, y=inset, width=inner_w, height=inner_h)

        if title:
            # Title bar spans the full width at the top of the inner frame.
            tk.Label(inner_frame, text=name, bg=self.lightest_grey, fg=self.text_color, font=("Arial", 14, "bold")).place(relx=0, rely=0, relwidth=1, anchor="nw")
        
        if not scrollable:
            return inner_frame

        # Scrollable sections wrap their content in a Canvas so a scrollbar can attach.
        canvas = tk.Canvas(inner_frame, bg=self.light_grey, highlightthickness=0)
        scrollbar = ttk.Scrollbar(inner_frame, orient="vertical", command=canvas.yview)
        scrollable_inner_frame = tk.Frame(canvas, bg=self.light_grey)
        window = canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")

        def update_scroll_visibility(event=None):
            # Hide the scrollbar when all content fits without scrolling.
            inner_frame.update_idletasks()
            content_height = scrollable_inner_frame.winfo_reqheight()
            visible_height = canvas.winfo_height()
            if content_height <= visible_height:
                scrollbar.place_forget()
                canvas.yview_moveto(0)
            else:
                scrollbar.place(relx=1, y=40, anchor="ne", height=inner_h - 40)
                canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_inner_frame.bind("<Configure>", update_scroll_visibility)

        def resize_scrollable_frame(event):
            # Keep the inner frame filling the canvas width when the window resizes.
            canvas.itemconfig(window, width=event.width)
            update_scroll_visibility()

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind/unbind mouse wheel only while the cursor is inside the scrollable area.
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        inner_frame.bind("<Enter>", _bind_to_mousewheel)
        inner_frame.bind("<Leave>", _unbind_from_mousewheel)
        canvas.bind("<Enter>", _bind_to_mousewheel)
        scrollable_inner_frame.bind("<Enter>", _bind_to_mousewheel)

        canvas.bind("<Configure>", resize_scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)
        # Place the canvas below the 40 px title bar.
        canvas.place(x=0, y=40, relwidth=1, height=inner_h - 40)
        
        return scrollable_inner_frame

    def build_interface(self):
        # Column 1: take-off queue on the far left.
        x_pos = self.margin_x
        self.takeoff_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Take-off Queue", scrollable=True)

        # Column 2: holding queue next to it.
        x_pos += self.col_w_standard + self.gap
        self.holding_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Holding Queue", scrollable=True)
    
        # Column 3 top: square display area for the airport visualisation.
        x_pos += self.col_w_standard + self.gap
        self.display_area_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_display, self.col_w_display, "Display", title=False)
        
        # Column 3 bottom: detail panel shown when a plane or runway is selected.
        y_pos_3_2 = self.margin_y + self.col_w_display + self.gap
        h_3_2 = self.top_col_h - self.col_w_display - self.gap
        self.display_info_frame = self.create_section(self.root, x_pos, y_pos_3_2, self.col_w_display, h_3_2, "Nothing Selected - Click on an Aircraft \n or Runway")

        # Column 4: runway list on the far right.
        x_pos += self.col_w_display + self.gap
        self.runway_queue_frame = self.create_section(self.root, x_pos, self.margin_y, self.col_w_standard, self.top_col_h, "Runways", scrollable=True)
    
        # Bottom strip: fixed-height control panel spanning the full width.
        panel_w = self.window_w - (2 * self.margin_x)
        panel_y = self.window_h - self.margin_y - self.panel_h
        control_panel_frame = self.create_section(self.root, self.margin_x, panel_y, panel_w, self.panel_h, "Control Panel", title=False)
        control_panel_frame.rowconfigure(0, weight=1)
        
        # Clock display on the far left of the control panel.
        self.clock_label = tk.Label(control_panel_frame, text="00:00", bg=self.lightest_grey, fg=self.text_color, font=("Arial", 17, "bold"))
        self.clock_label.grid(column=0, row=0, sticky="nsew", padx=[7,5], pady=7, ipadx=5)

        # Action buttons are spaced evenly across the rest of the panel.
        tk.Button(control_panel_frame, text="Pause/Continue [P]", bg=self.lightest_grey, font=("Arial", 12, "bold", "underline"), padx=5, relief="flat", command=self.toggle_pause).grid(column=1, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="Simulation Settings [S]", bg=self.lightest_grey, font=("Arial", 12, "bold", "underline"), padx=5, relief="flat", command=self.open_simulation_settings).grid(column=2, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="View Statistics [V]", bg=self.lightest_grey, font=("Arial", 12, "bold", "underline"), padx=5, relief="flat", command=self.open_statistics).grid(column=3, row=0, sticky="nsew", padx=5, pady=7)
        tk.Button(control_panel_frame, text="Reset Simulation [R]", bg=self.lightest_grey, font=("Arial", 12, "bold", "underline"), padx=5, relief="flat", command=self.reset_simulation).grid(column=4, row=0, sticky="nsew", padx=5, pady=7)

    # --- Popups (Using Toplevel) ---
    
    def open_simulation_settings(self, event=None):
        # Bring an existing settings window to the front rather than opening a duplicate.
        if hasattr(self, 'settings_win') and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
            
        # Pause while the user adjusts settings so nothing runs in the background.
        self.toggle_pause(force_pause=True)
        
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Simulation Settings")
        self.settings_win.geometry("450x450")
        self.settings_win.configure(bg=self.dark_grey)
        self.settings_win.grab_set()  # Block interaction with the main window.
        self.settings_win.resizable(False, False)
        
        container = tk.Frame(self.settings_win, bg=self.lightest_grey, padx=20, pady=20)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Label(container, text="Adjust Simulation Parameters", font=("Arial", 16, "bold"), bg=self.lightest_grey).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        entries = {}
        def add_setting(row, label_text, default_val):
            # Helper that adds a label/entry pair and registers the entry in the dict.
            tk.Label(container, text=label_text, bg=self.lightest_grey, font=("Arial", 11, "bold")).grid(row=row, column=0, sticky="w", pady=5)
            entry = ttk.Entry(container, font=("Arial", 11), width=10)
            entry.insert(0, str(default_val))
            entry.grid(row=row, column=1, sticky="e", pady=5)
            entries[label_text] = entry

        # Read current values from the engine so the dialog always reflects live state.
        p = getattr(self.engine, 'params', None)
        curr_runways = len(self.engine.airport.runways) if hasattr(self.engine, 'airport') else 3
        curr_speed = getattr(self.engine, 'speed_multiplier', 1.0)
        
        add_setting(1, "Number Of Runways:", curr_runways)
        add_setting(2, "Inbound flow (per hour):", getattr(p, 'inbound_rate_per_hour', 10) if p else 10)
        add_setting(3, "Outbound flow (per hour):", getattr(p, 'outbound_rate_per_hour', 10) if p else 10)
        add_setting(4, "Simulation speed multiplier:", curr_speed)
        add_setting(5, "Max take off wait (mins):", getattr(p, 'max_takeoff_wait_min', 30.0) if p else 30.0)
        add_setting(6, "Min fuel levels (mins):", getattr(p, 'fuel_min_min', 10.0) if p else 10.0)
        # Emergency rate is stored internally as two separate probabilities; combine them for display.
        emerg_rate = (getattr(p, 'p_mechanical_failure', 0.15) * 2) if p else 0.3
        add_setting(7, "Rate of emergencies:", emerg_rate)

        def apply():
            try:
                self.apply_parameters(
                    int(entries["Number Of Runways:"].get()),
                    float(entries["Inbound flow (per hour):"].get()),
                    float(entries["Outbound flow (per hour):"].get()),
                    float(entries["Simulation speed multiplier:"].get()),
                    float(entries["Max take off wait (mins):"].get()),
                    float(entries["Min fuel levels (mins):"].get()),
                    float(entries["Rate of emergencies:"].get())
                )
                self.settings_win.destroy()
                self.toggle_pause(force_play=True)
            except ValueError:
                # Show an inline error rather than crashing if the user typed non-numbers.
                tk.Label(container, text="Invalid input: use numbers only", fg="red", bg=self.lightest_grey).grid(row=9, column=0, columnspan=2)
            except Exception as e:
                tk.Label(container, text=f"Apply Error: {str(e)[:40]}", fg="red", bg=self.lightest_grey).grid(row=9, column=0, columnspan=2)
                print(f"Apply error: {e}")

        tk.Button(container, text="Apply Changes", bg=self.medium_grey, fg="white", font=("Arial", 12, "bold"), command=apply).grid(row=8, column=0, columnspan=2, pady=20, ipadx=20)

    def open_statistics(self, event=None):
        # Bring an existing stats window to the front rather than opening a duplicate.
        if hasattr(self, 'stats_win') and self.stats_win.winfo_exists():
            self.stats_win.lift()
            return

        self.toggle_pause(force_pause=True)
        self.stats_win = tk.Toplevel(self.root)
        self.stats_win.title("Statistical Report")
        self.stats_win.geometry("500x450")
        self.stats_win.configure(bg=self.dark_grey)
        self.stats_win.grab_set()
        
        container = tk.Frame(self.stats_win, bg=self.lightest_grey, padx=20, pady=20)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Label(container, text="Live Statistical Report", font=("Arial", 16, "bold"), bg=self.lightest_grey).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Pull a snapshot of stats from the engine at the moment the dialog opens.
        report_data = self.engine.get_report()
        
        def add_stat(row, label, val):
            tk.Label(container, text=label, bg=self.lightest_grey, font=("Arial", 11, "bold")).grid(row=row, column=0, sticky="w", pady=2)
            tk.Label(container, text=str(val), bg=self.lightest_grey, font=("Arial", 11)).grid(row=row, column=1, sticky="e", pady=2)
            
        add_stat(1, "Max holding queue size:", report_data.get("maxHoldingQueue", 0))
        add_stat(2, "Avg holding queue size:", report_data.get("avgHoldingQueue", 0))
        add_stat(3, "Max holding queue wait time (m):", report_data.get("maxArrivalDelay", 0))
        add_stat(4, "Avg holding queue wait time (m):", report_data.get("avgHoldingTime", 0))
        add_stat(5, "Max take off queue size:", report_data.get("maxTakeoffQueue", 0))
        add_stat(6, "Avg take off queue size:", report_data.get("avgArrivalDelay", 0))
        add_stat(7, "Max take off queue wait time (m):", report_data.get("maxTakeoffWait", 0))
        add_stat(8, "Avg take off queue wait time (m):", report_data.get("avgTakeoffWait", 0))
        add_stat(9, "Total inbound diversions:", report_data.get("diversions", 0))
        add_stat(10, "Total outbound cancellations:", report_data.get("cancellations", 0))
        add_stat(11, "Total simulation time:", self.format_time(self.engine.get_time()))
        
        # Closing the stats window resumes the simulation automatically.
        tk.Button(container, text="Close", bg=self.medium_grey, fg="white", font=("Arial", 12, "bold"), command=lambda: [self.stats_win.destroy(), self.toggle_pause(force_play=True)]).grid(row=12, column=0, columnspan=2, pady=20, ipadx=20)

    # --- Data Application & Runway Degradation ---

    def apply_parameters(self, num_runways, in_flow, out_flow, speed_mult, max_wait, min_fuel, emerg_rate):
        # Build a fresh SimulationParams because the existing one may be frozen/immutable.
        params = SimulationParams(
            num_runways=num_runways,
            inbound_rate_per_hour=in_flow,
            outbound_rate_per_hour=out_flow,
            max_takeoff_wait_min=int(max_wait),
            arrival_stddev_min=5,
            departure_stddev_min=5,
            emergencies_per_tick=0,
            tick_size_min=1,
            # The combined emergency rate is split evenly across the two failure types.
            p_mechanical_failure=emerg_rate / 2,
            p_passenger_illness=emerg_rate / 2,
            p_fuel_emergency=0.0,
            fuel_emergency_min=15,
            fuel_min_min=int(min_fuel)
        )
        
        # Speed multiplier is stored on the engine object, not inside SimulationParams.
        self.engine.speed_multiplier = speed_mult
        self.engine.params = params

        current_runways = list(self.engine.airport.runways)
        current_count = len(current_runways)
        
        if num_runways > current_count:
            # Add new runways, continuing IDs from the current highest to avoid clashes.
            highest_id = max([r.id for r in current_runways]) if current_runways else 0
            for i in range(num_runways - current_count):
                highest_id += 1
                current_runways.append(Runway(runway_id=highest_id, runway_mode="MIXED"))
            self.engine.airport.runways = current_runways
        
        elif num_runways < current_count:
            # Don't remove busy runways immediately; flag them and wait for them to clear.
            runways_to_flag = current_runways[num_runways:]
            for r in runways_to_flag:
                if r not in self.pending_runway_removals:
                    self.pending_runway_removals.append(r)
                    r.status = "Closed"
            self.engine.airport.runways = current_runways
        
        self.update_ui()

    # --- Core Simulation Loop ---

    def toggle_pause(self, force_pause=False, force_play=False):
        if force_pause:
            self.engine.is_paused = True
        elif force_play:
            self.engine.is_paused = False
        else:
            self.engine.is_paused = not self.engine.is_paused
            
        if self.engine.is_paused:
            # Cancel any scheduled callbacks so no ticks fire while paused.
            if self.sim_loop_id:
                self.root.after_cancel(self.sim_loop_id)
                self.sim_loop_id = None
            if self.smooth_loop_id:
                self.root.after_cancel(self.smooth_loop_id)
                self.smooth_loop_id = None
        else:
            # Reset the real-time reference so the first smooth frame isn't skewed.
            self.last_tick_real_time = time.time()
            self.simulation_tick()
            self.smooth_update()

    def reset_simulation(self):
        # Pause immediately so no ticks fire while we're tearing state down.
        self.toggle_pause(force_pause=True)

        # Zero out the simulation clock.
        self.engine.current_time = 0

        # Replace stats and make sure the airport reference points to the same object.
        # The original bug was that airport.stats kept pointing to the old instance.
        new_stats = Statistics()
        self.engine.stats = new_stats
        self.engine.airport.stats = new_stats

        # Clear both queues using the correct attribute names (holding / takeoff).
        self.engine.airport.holding = HoldingQueue()
        self.engine.airport.takeoff = TakeOffQueue()

        # Discard pending aircraft lists or they'd flood the queues on the first tick.
        self.engine._pending_inbound.clear()
        self.engine._pending_outbound.clear()
        self.pending_status_changes.clear()
        self.pending_runway_removals.clear()

        # Zero the spawn accumulators; leftover fractions would cause near-instant spawns.
        self.engine._inbound_acc = 0.0
        self.engine._outbound_acc = 0.0

        # Reset ID counters so callsigns start from the beginning again.
        self.engine._next_in_id = 1
        self.engine._next_out_id = 1

        # Return every runway to a clean idle state.
        for runway in self.engine.airport.runways:
            runway.currentAircraft = None
            runway.currentOperation = None
            runway.status = "AVAILABLE"
            runway.occupancy = "FREE"
            runway.startTime = 0
            runway.duration = 0
            runway.occupiedUntil = 0

        # Wipe all plane and runway widgets from the UI.
        self.pending_runway_removals.clear()

        for widget in list(self.holding_plane_widgets.values()):
            widget["frame"].destroy()
        self.holding_plane_widgets.clear()

        for widget in list(self.takeoff_plane_widgets.values()):
            widget["frame"].destroy()
        self.takeoff_plane_widgets.clear()

        for widget in list(self.runway_widgets.values()):
            widget["frame"].destroy()
        self.runway_widgets.clear()

        # Restore the detail panel to its default prompt text.
        for w in self.display_info_frame.winfo_children():
            w.destroy()
        tk.Label(
            self.display_info_frame,
            text="Nothing Selected - Click on an Aircraft \n or Runway",
            bg=self.lightest_grey,
            font=("Arial", 14, "bold")
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Explicitly mark the engine as running again before reopening settings.
        self.engine.is_paused = False

        # Refresh the empty UI, then let the user reconfigure before restarting.
        self.update_ui()
        self.open_simulation_settings()

    def simulation_tick(self):
        if self.engine.is_paused: 
            return

        self.engine.tick()
        self.last_tick_real_time = time.time()

        # Remove any flagged runways that have now finished their last operation.
        for r in self.pending_runway_removals[:]:
            if r.currentAircraft is None or r.occupancy == "FREE":
                current_list = list(self.engine.airport.runways)
                if r in current_list:
                    current_list.remove(r)
                    self.engine.airport.runways = current_list
                self.pending_runway_removals.remove(r)

        # Apply deferred status changes for runways that have just cleared.
        for r in list(self.pending_status_changes):
            if r.currentAircraft is None:
                next_status, wf, pc, pgs = self.pending_status_changes.pop(r)
                r.status = next_status
                self._apply_status_visuals(next_status, wf, pc, pgs)
                
        self.update_ui()

        # Scale the tick interval by the speed multiplier so faster speeds tick more often.
        try:
            speed = float(getattr(self.engine, 'speed_multiplier', 1.0))
            interval = int(1000 / speed) if speed > 0 else 1000
        except:
            interval = 1000
        self.sim_loop_id = self.root.after(interval, self.simulation_tick)

    def smooth_update(self):
        # Skip smoothing entirely when paused.
        if self.engine.is_paused: return
        try:
            speed = float(getattr(self.engine, 'speed_multiplier', 1.0))
            tick_duration_ms = 1000 / speed if speed > 0 else 1000
            real_time_passed = (time.time() - self.last_tick_real_time) * 1000
            # Fraction of the current tick that has elapsed in real time (clamped to 1).
            tick_fraction = min(1.0, real_time_passed / tick_duration_ms)

            # Snapshot active aircraft so we can interpolate their progress bars.
            active_aircraft_data = {}
            for r in self.engine.get_runways():
                if r.currentAircraft and r.occupancy == "OCCUPIED":
                    active_aircraft_data[r.currentAircraft.callsign] = {
                        "start": r.startTime,
                        "duration": getattr(r, 'duration', 1)
                    }

            # Smoothly advance the runway progress bars between ticks.
            for r in self.engine.get_runways():
                if r.id in self.runway_widgets:
                    w = self.runway_widgets[r.id]
                    if r.currentAircraft and r.currentAircraft.callsign in active_aircraft_data:
                        data = active_aircraft_data[r.currentAircraft.callsign]
                        elapsed = self.engine.get_time() - data["start"]
                        smooth_val = ((elapsed + tick_fraction) / max(data["duration"], 1)) * 100
                        w["progress"]["value"] = min(100, smooth_val)
                    else:
                        w["progress"]["value"] = 0

            # Also smooth any plane widgets that are currently on a runway.
            all_plane_widgets = {**self.holding_plane_widgets, **self.takeoff_plane_widgets}
            for cs, widget in all_plane_widgets.items():
                if cs in active_aircraft_data:
                    data = active_aircraft_data[cs]
                    elapsed = self.engine.get_time() - data["start"]
                    smooth_val = ((elapsed + tick_fraction) / max(data["duration"], 1)) * 100
                    widget["progress"]["value"] = min(100, smooth_val)
                else:
                    widget["progress"]["value"] = 0
        except Exception as e: 
            pass  # Silently swallow errors here to avoid spamming the console.
            
        # Schedule the next frame at roughly 60 fps (16 ms).
        self.smooth_loop_id = self.root.after(16, self.smooth_update)

    def update_ui(self):
        all_runways = self.engine.get_runways()
        # Prepend aircraft currently on a runway so they appear at the top of their queue.
        active_inbound = [r.currentAircraft for r in all_runways if r.currentAircraft and r.currentAircraft.type == "INBOUND"]
        full_holding_list = active_inbound + self.engine.get_holding_queue()
        active_outbound = [r.currentAircraft for r in all_runways if r.currentAircraft and r.currentAircraft.type == "OUTBOUND"]
        full_takeoff_list = active_outbound + self.engine.get_takeoff_queue()
        
        self.update_plane_queue(full_holding_list, self.holding_queue_frame, self.holding_plane_widgets)
        self.update_plane_queue(full_takeoff_list, self.takeoff_queue_frame, self.takeoff_plane_widgets)
        self.update_runway_queue(all_runways, self.runway_queue_frame, self.runway_widgets)
        self.clock_label.config(text=f"{self.format_time(self.engine.get_time())}")

    # --- Widget Creators/Updaters ---

    def format_time(self, time_var):
        # Convert a raw minute counter into HH:MM, wrapping at midnight.
        hours = (time_var // 60) % 24
        minutes = time_var % 60
        return f"{hours:02d}:{minutes:02d}"

    def update_plane_queue(self, queue, frame, widget_dict):
        current_ids = set()
        for plane in queue:
            pid = plane.callsign
            current_ids.add(pid)
            # Create a widget for planes we haven't seen before, then update it.
            if pid not in widget_dict:
                widget_dict[pid] = self.create_plane_widget(frame, plane)
            self.update_plane_widget(widget_dict[pid], plane)
        # Destroy widgets for planes that are no longer in the queue.
        for pid in list(widget_dict):
            if pid not in current_ids:
                widget_dict[pid]["frame"].destroy()
                if self.selected_widget == widget_dict[pid]:
                    self.selected_widget = None
                del widget_dict[pid]

    def create_plane_widget(self, queue_column, plane):
        widget_frame = tk.Frame(queue_column, bg=self.lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)
        # Six labels laid out as a 3-row grid: top-left/right, mid-left/right, bottom-left/right.
        tl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 13, "bold"), anchor="w")
        tr = tk.Label(widget_frame, text="", bg=self.lightest_grey, fg=self.emergency_text_color, font=("Arial", 11, "bold"), anchor="e")
        ml = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 11), anchor="w")
        mr = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 5), anchor="e")
        bl = tk.Label(widget_frame, text="[Progress]", bg=self.lightest_grey, font=("Arial", 11, "bold"), anchor="w")
        br = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 11), anchor="e")
        tl.grid(row=0, column=0, sticky="w")
        tr.grid(row=0, column=1, sticky="e")
        ml.grid(row=1, column=0, sticky="w")
        mr.grid(row=1, column=1, sticky="e")
        bl.grid(row=2, column=0, sticky="w")
        br.grid(row=2, column=1, sticky="e")
        # Progress bar sits in its own container frame so height can be fixed.
        pc = tk.Frame(widget_frame, height=13, bg=self.lightest_grey)
        pc.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        pc.pack_propagate(False)
        progress = ttk.Progressbar(pc, orient="horizontal", mode="determinate")
        progress.pack(fill="both", expand=True)

        # widget_ref is populated below so the closure captures the final dict.
        widget_ref = {}

        def on_click(e):
            self.select_widget(widget_ref)
            self.show_airplane_info(plane)

        widget_frame.bind("<Button-1>", on_click)
        for lbl in (tl, tr, ml, mr, bl, br): lbl.bind("<Button-1>", on_click)

        widget_ref.update({ "frame": widget_frame, "tl": tl, "tr": tr, "ml": ml, "br": br, "progress": progress })
        return widget_ref

    def update_plane_widget(self, widget, plane):
        # Determine the highest-priority emergency to display, if any.
        emerg = ""
        if hasattr(plane, 'emergency') and plane.emergency:
            if plane.emergency.mechanical_failure: emerg = "Mechanical Failure"
            elif plane.emergency.passenger_illness: emerg = "Passenger Illness"
            elif plane.emergency.fuel_emergency: emerg = "Fuel Emergency"
        widget["tl"].config(text=plane.callsign)
        widget["tr"].config(text=emerg)
        widget["ml"].config(text=getattr(plane, 'operator', 'Unknown'))
        widget["br"].config(text="Scheduled " + self.format_time(getattr(plane, 'scheduledTime', 0)))
        # Inbound uses orange, outbound uses green, matching the progress bar styles.
        style = "Orange.Horizontal.TProgressbar" if plane.type == "INBOUND" else "Green.Horizontal.TProgressbar"
        widget["progress"].config(style=style)

    def update_runway_queue(self, queue, frame, widget_dict):
        current_ids = set()
        for rw in queue:
            rid = rw.id
            current_ids.add(rid)
            if rid not in widget_dict:
                widget_dict[rid] = self.create_runway_widget(frame, rw)
            self.update_runway_widget(widget_dict[rid], rw)
        # Remove widgets for runways that no longer exist.
        for rid in list(widget_dict):
            if rid not in current_ids:
                widget_dict[rid]["frame"].destroy()
                if self.selected_widget == widget_dict[rid]:
                    self.selected_widget = None
                del widget_dict[rid]

    def create_runway_widget(self, queue_col, rw):
        widget_frame = tk.Frame(queue_col, bg=self.lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)
        # Progress bar container, fixed at 13 px tall.
        pc = tk.Frame(widget_frame, height=13, bg=self.lightest_grey)
        pc.pack_propagate(False)
        pg_settings = {"row": 3, "column": 0, "columnspan": 2, "sticky": "ew", "pady": (5, 0)}
        pc.grid(**pg_settings)
        progress = ttk.Progressbar(pc, orient="horizontal", mode="determinate")
        progress.pack(fill="both", expand=True)
        # Status and mode buttons are stacked in a small frame on the right.
        bf = tk.Frame(widget_frame, bg=self.lightest_grey)
        bf.grid(row=0, column=1, sticky="ne")
        tk.Button(bf, text="Status", bg=self.lightest_grey, padx=5, relief="solid", command=lambda r=rw, wf=widget_frame, c=pc: self.cycle_runway_status(r, wf, c, pg_settings)).pack(side="right", padx=(2, 0))
        tk.Button(bf, text="Mode", bg=self.lightest_grey, padx=5, relief="solid", command=lambda: self.cycle_runway_mode(rw)).pack(side="right")
        tl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 12, "bold"), anchor="w")
        bl = tk.Label(widget_frame, text="", bg=self.lightest_grey, font=("Arial", 10, "bold"), anchor="w")
        tl.grid(row=0, column=0, sticky="w")
        bl.grid(row=2, column=0, sticky="w")
        # Status text in emergency red on the bottom-right.
        br = tk.Label(widget_frame, text="Status", bg=self.lightest_grey, fg=self.emergency_text_color, font=("Arial", 9, "bold"), anchor="e")
        br.grid(row=2, column=1, sticky="e")

        widget_ref = {}

        def on_click(e):
            # Only allow selection highlighting when the runway is available.
            if rw.status == "AVAILABLE":
                self.select_widget(widget_ref)
            self.show_runway_info(rw)

        widget_frame.bind("<Button-1>", on_click)
        for lbl in (tl, bl, br): lbl.bind("<Button-1>", on_click)

        widget_ref.update({ "frame": widget_frame, "tl": tl, "bl": bl, "br": br, "progress": progress })
        return widget_ref

    def update_runway_widget(self, widget, rw):
        # Build the title string, adding suffix tags for closing or clearing states.
        if rw.mode == "LANDING": title = f"Runway {rw.id} - Landing Only"
        elif rw.mode == "TAKEOFF": title = f"Runway {rw.id} - Take Off Only"
        else: title = f"Runway {rw.id} - Mixed Use"

        if rw in self.pending_runway_removals:
            title += " (CLOSING)"

        pending = self.pending_status_changes.get(rw)
        if pending:
            title += f" (Clearing)"

        if rw.currentAircraft is None:
            airplane_txt = "Not currently in use"
        else:
            dir = "Landing" if rw.currentAircraft.type == "INBOUND" else "Taking Off"
            airplane_txt = f"{rw.currentAircraft.callsign} - {dir}"

        widget["tl"].config(text=title)
        widget["bl"].config(text=airplane_txt)
        # Show nothing in the status label when the runway is available.
        status_display = "" if rw.status == "AVAILABLE" else rw.status
        widget["br"].config(text=status_display)

        # Match bar colour to the type of operation currently underway.
        op = getattr(rw, 'currentOperation', '')
        style = "Orange.Horizontal.TProgressbar" if op == "LANDING" else "Green.Horizontal.TProgressbar"
        widget["progress"].config(style=style)

    def cycle_runway_mode(self, rw):
        # Prevent mode changes on runways already queued for removal.
        if rw in self.pending_runway_removals: return
        if rw.mode == "LANDING": rw.mode = "MIXED"
        elif rw.mode == "MIXED": rw.mode = "TAKEOFF"
        else: rw.mode = "LANDING"
        self.update_ui()

    def update_widget_colors(self, widget, color):
        # Recursively recolour a widget and all its children, skipping non-bg widgets.
        if not isinstance(widget, (ttk.Progressbar, tk.Button)):
            widget.configure(bg=color)
        for child in widget.winfo_children(): self.update_widget_colors(child, color)

    def _apply_status_visuals(self, new_status, wf, pc, pgs):
        # Available runways look normal; any other status gets a greyed-out, bordered look.
        if new_status == "AVAILABLE":
            bg, rel, bord, show_prog = self.lightest_grey, "flat", 0, True
        else:
            bg, rel, bord, show_prog = self.light_grey, "solid", 1, False
        wf.config(bg=bg, relief=rel, borderwidth=bord)
        self.update_widget_colors(wf, bg)
        # Hide the progress bar when the runway isn't available for use.
        if show_prog:
            pc.grid(**pgs)
        else:
            pc.grid_forget()

    def cycle_runway_status(self, rw, wf, pc, pgs):
        if rw in self.pending_runway_removals:
            return

        # To re-add statuses like "Runway Inspection", extend this list.
        status_order = ["AVAILABLE", "Closed"]
        current = self.pending_status_changes.get(rw, rw.status)
        next_status = status_order[(status_order.index(current) + 1) % len(status_order)]

        if rw.currentAircraft is None:
            # Runway is free, so apply the new status straight away.
            rw.status = next_status
            self.pending_status_changes.pop(rw, None)  # Clear any stale pending entry.
            self._apply_status_visuals(next_status, wf, pc, pgs)
        else:
            # Set the status immediately to stop new assignments, but defer the visual
            # update until the plane currently using the runway has departed.
            rw.status = next_status
            self.pending_status_changes[rw] = (next_status, wf, pc, pgs)

        self.update_ui()

    # --- Info Displays ---

    def show_airplane_info(self, airplane):
        # Clear whatever was shown before and rebuild with this aircraft's data.
        for w in self.display_info_frame.winfo_children(): w.destroy()
        tk.Label(self.display_info_frame, text=f"Aircraft {airplane.callsign}", bg=self.lightest_grey, font=("Arial", 14, "bold")).place(x=0, y=0, relwidth=1)
        f = tk.Frame(self.display_info_frame, bg=self.lightest_grey)
        f.place(x=0, y=30, relwidth=1, relheight=1)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        def add(r, l, v):
            tk.Label(f, text=l, bg=self.lightest_grey, font=("Arial", 10, "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=10, pady=2)
            tk.Label(f, text=str(v), bg=self.lightest_grey, font=("Arial", 10, "bold"), anchor="e").grid(row=r, column=1, sticky="e", padx=10, pady=2)
        add(0, "Operator:", getattr(airplane, 'operator', 'N/A'))
        add(1, "Origin:", getattr(airplane, 'origin', 'N/A'))
        add(2, "Destination:", getattr(airplane, 'destination', 'N/A'))
        add(3, "Fuel Level:", getattr(airplane, 'fuelRemaining', 'N/A'))
        add(4, "Altitude:", getattr(airplane, 'altitude', 'N/A'))
        add(5, "Ground Speed:", getattr(airplane, 'ground_speed', 'N/A'))
        add(6, "Scheduled:", self.format_time(getattr(airplane, 'scheduledTime', 0)))

    def show_runway_info(self, rw):
        # Clear whatever was shown before and rebuild with this runway's data.
        for w in self.display_info_frame.winfo_children(): w.destroy()
        tk.Label(self.display_info_frame, text=f"Runway {rw.id}", bg=self.lightest_grey, font=("Arial", 14, "bold")).place(x=0, y=0, relwidth=1)
        f = tk.Frame(self.display_info_frame, bg=self.lightest_grey)
        f.place(x=0, y=30, relwidth=1, relheight=1)
        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        def add(r, l, v):
            tk.Label(f, text=l, bg=self.lightest_grey, font=("Arial", 10, "bold"), anchor="w").grid(row=r, column=0, sticky="w", padx=10, pady=2)
            tk.Label(f, text=str(v), bg=self.lightest_grey, font=("Arial", 10, "bold"), anchor="e").grid(row=r, column=1, sticky="e", padx=10, pady=2)
        add(0, "Operating Mode:", rw.mode)
        add(1, "Occupancy:", rw.occupancy)
        add(2, "Status:", rw.status)
        add(3, "Length:", f"{getattr(rw, 'length', 'N/A')} m")
        bearing_str = rw.getBearingString() if hasattr(rw, 'getBearingString') else "N/A"
        add(4, "Bearing:", bearing_str)

    def select_widget(self, widget):
        # Deselect the previously highlighted widget before applying the new selection.
        if self.selected_widget:
            self.update_widget_colors(self.selected_widget["frame"], self.lightest_grey)
        self.selected_widget = widget
        self.update_widget_colors(widget["frame"], "#c8c6c6")  # Slightly darker than the default background.

def create_ui(engine):
    root = tk.Tk()
    app = AirportUI(root, engine)
    root.mainloop()