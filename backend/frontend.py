#this file is temporarily in backend as we dont have a working main.py (yet) and other files need to be accessed

# things still TODO:
# Angelina this week:
# link with backend + remove testing code
# aircraft failure warning signs
# pause
# reset simulation 
# time
# making statistic outputs look good
# additional info on aircraft widgets 
# mouse/trackpad scrolling

# Will:
# progress bars - DONE
# plane/runway display - HARD TO DO
# display caption - ^^ Alongside Display
# button images - ^^ Doing next

import tkinter as tk
from aircraft import Aircraft
from runway import Runway
from statistics import Statistics
from tkinter import ttk # For Progress Bars
#from SimulationParameters import SimulationParams

def create_ui():
    root = tk.Tk()

    # Dimensions
    window_w = root.winfo_screenwidth() - 100
    window_h = root.winfo_screenheight() - 100

    # Margins and gaps
    margin_x = window_w / 96
    margin_y = window_h / 54
    gap = window_w / 120
   
    # Width and height of columns
    col_w_standard = window_w * (7/32)
    col_w_display = window_w * (143/480)
    panel_h = window_h * (11/180)
    top_col_h = window_h - (2 * margin_y) - panel_h - gap
   
    # Colors
    dark_grey = "#2b2b2b"
    medium_grey = "#404040"
    light_grey = "#5c5c5c"
    lightest_grey = "#A6A4A4"
    text_color = "#000000"
    emergency_text_color = "#bf0000"
   
    # Progress Bar Custom Styling
    style = ttk.Style()
    style.theme_use('clam') # 'clam' is required to allow color overrides
    style.configure("Green.Horizontal.TProgressbar", foreground='green', background='green', thickness=15)
    style.configure("Orange.Horizontal.TProgressbar", foreground='orange', background='orange', thickness=15)
    style.configure("Vertical.TScrollbar", 
                        gripcount=0,
                        background=lightest_grey, 
                        troughcolor=medium_grey, 
                        bordercolor=dark_grey, 
                        arrowcolor=medium_grey,
                        arrowsize=13)

    style.map("Vertical.TScrollbar",
                background=[('active', "#dcdad5"), ('disabled', lightest_grey)],
                troughcolor=[('active', medium_grey), ('disabled', medium_grey)])

    root.title("Airport Simulation")
    root.geometry(f"{window_w}x{window_h}")
    root.configure(bg=dark_grey)

    root.bind("P", lambda x: pause())
    root.bind("p", lambda x: pause())
    root.bind("S", lambda x: create_simulation_settings())
    root.bind("s", lambda x: create_simulation_settings())
    root.bind("V", lambda x: create_statistics())
    root.bind("v", lambda x: create_statistics())
    root.bind("R", lambda x: reset_simulation())
    root.bind("r", lambda x: reset_simulation())
    root.resizable(False, False)

    # Helper function to create sections with inset rectangles
    def create_section(parent, x, y, w, h, name, title = True, scrollable = False):
        # Create the outer frame (The container/border)
        outer_frame = tk.Frame(parent, bg=medium_grey, width=w, height=h)
        outer_frame.place(x=x, y=y)
        
        # Create the inner frame (The inset)
        # 4px margin on all sides means width and height are reduced by 8px total
        inset = 4
        inner_w = w - (inset * 2)
        inner_h = h - (inset * 2)
        inner_frame = tk.Frame(outer_frame, bg=light_grey, width=inner_w, height=inner_h)
        inner_frame.place(x=inset, y=inset)

        if title:
        # Label placed inside the inner_frame
            tk.Label(inner_frame, text=name, bg=lightest_grey, fg=text_color, font=("Arial", 14, "bold")).place(relx=0, rely=0, relwidth=1, anchor="nw")
        
        # If not a scrollable section, returns inner_frame for us, as that is where future widgets will go
        if not scrollable:
            return inner_frame

        # Otherwise, allows for scrolling inside the frame
        canvas = tk.Canvas(inner_frame, bg=light_grey, highlightthickness=0)
        scrollbar = ttk.Scrollbar(inner_frame, orient="vertical", command=canvas.yview)

        scrollable_inner_frame = tk.Frame(canvas, bg=light_grey)
        
        window = canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")

        # Functionality to hide the scrollbar when not needed
        def update_scroll_visibility(event=None):
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
            canvas.itemconfig(window, width=event.width)
            update_scroll_visibility()

        # Functionality to scroll with mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        # These events trigger when the mouse enters or leaves the section
        inner_frame.bind("<Enter>", _bind_to_mousewheel)
        inner_frame.bind("<Leave>", _unbind_from_mousewheel)
        # Also bind to the canvas and scrollable_inner_frame so children don't block it
        canvas.bind("<Enter>", _bind_to_mousewheel)
        scrollable_inner_frame.bind("<Enter>", _bind_to_mousewheel)

        canvas.bind("<Configure>", resize_scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.place(x=0, y=40, relwidth=1, height=inner_h - 40)
        
        return scrollable_inner_frame

    # Helper function to create each plane widget (now created as a Frame!)
    def create_plane_widget(queue_column, plane):
        # Create a Frame (Used to be Button)
        widget_frame = tk.Frame(queue_column, bg=lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))

        # Configure the grid inside the frame (2 equal columns)
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)

        # Create the 6 text labels
        tl = tk.Label(widget_frame, text=plane.callsign, bg=lightest_grey, font=("Arial", 13, "bold"), anchor="w")
        tr = tk.Label(widget_frame, text="[Emergency]", bg=lightest_grey, fg=emergency_text_color, font=("Arial", 11, "bold"), anchor="e")
        
        ml = tk.Label(widget_frame, text=plane.operator, bg=lightest_grey, font=("Arial", 11), anchor="w")
        mr = tk.Label(widget_frame, text="", bg=lightest_grey, font=("Arial", 5), anchor="e")
        
        bl = tk.Label(widget_frame, text="[Progress]", bg=lightest_grey, font=("Arial", 11, "bold"), anchor="w")
        br = tk.Label(widget_frame, text="Scheduled " + format_time(plane.scheduledTime), bg=lightest_grey, font=("Arial", 11), anchor="e")

        # Place them in the grid
        tl.grid(row=0, column=0, sticky="w")
        tr.grid(row=0, column=1, sticky="e")
        ml.grid(row=1, column=0, sticky="w")
        mr.grid(row=1, column=1, sticky="e")
        bl.grid(row=2, column=0, sticky="w")
        br.grid(row=2, column=1, sticky="e")

        # Add the Progress Bar at the bottom (Row 3, spanning both columns)
        
        # Create a container frame with a strict height
        progress_container = tk.Frame(widget_frame, height=13, bg=lightest_grey)
        progress_container.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        # Prevents the frame from expanding to fit the progress bar
        progress_container.pack_propagate(False) 

        # Create the progress bar inside the container and set it to fill the space
        progress = ttk.Progressbar(progress_container, orient="horizontal", mode="determinate")
        progress.pack(fill="both", expand=True)
        progress['value'] = 50 # Placeholder for logic

        # Make the whole frame and its labels clickable
        def on_click(event):
            airplane_selected(plane)
            
        widget_frame.bind("<Button-1>", on_click)
        # Bind the click to the labels too, so clicking text works
        for label in (tl, tr, ml, mr, bl, br):
            label.bind("<Button-1>", on_click)

    # Helper function to create each runway widget (now using Frame instead of Button)
    def create_runway_widget(runway_column, runway):
        if runway.mode == "LANDING":
            runway_title_readable = "Runway "+ str(runway.id) + " - Landing only"
        elif runway.mode == "TAKEOFF":
            runway_title_readable = "Runway "+ str(runway.id) + " - Take off only"
        else:
            runway_title_readable = "Runway "+ str(runway.id) + " - Mixed Use"

        if runway.currentAircraft == None:
            runway_airplane_readable = "Not currently in use"
        else:
            direction = "Landing" if runway.currentAircraft.type == "INBOUND" else "Taking off"
            runway_airplane_readable = f"{runway.currentAircraft.callsign} - {direction}"

        emergency_readable = "Fire"

        # Main container frame
        widget_frame = tk.Frame(runway_column, bg=lightest_grey, padx=5, pady=5, cursor="hand2")
        widget_frame.pack(fill="x", pady=4, padx=(4, 22))
        widget_frame.columnconfigure(0, weight=1)
        widget_frame.columnconfigure(1, weight=1)

        # Create the container
        progress_container = tk.Frame(widget_frame, height=13, bg=lightest_grey)
        progress_container.pack_propagate(False) 
        # Store the grid settings in a dictionary for easy re-application
        pg_settings = {"row": 3, "column": 0, "columnspan": 2, "sticky": "ew", "pady": (5, 0)}
        progress_container.grid(**pg_settings)

        # Add the Progress Bar at the bottom (Row 3, spanning both columns)
        bar_style = "Orange.Horizontal.TProgressbar" if runway.currentOperation == "LANDING" else "Green.Horizontal.TProgressbar"
        progress = ttk.Progressbar(progress_container, orient="horizontal", mode="determinate", style=bar_style)
        progress.pack(fill="both", expand=True)
        progress['value'] = 25

        # Create Buttons
        button_frame = tk.Frame(widget_frame, bg=lightest_grey)
        button_frame.grid(row=0, column=1, sticky="ne")

        # Status and Mode Buttons
        operating_mode = tk.Button(button_frame, text="B", bg=light_grey, padx=5, relief="solid", command=lambda: change_operating_mode(runway))
        operating_mode.pack(side="right", padx=(2, 0))

        status_button = tk.Button(button_frame, text="A", bg=light_grey, padx=5, relief="solid", command=lambda r=runway, wf=widget_frame, pc=progress_container: change_status(r, wf, pc, pg_settings))
        status_button.pack(side="right")

        # Labels for Left Side
        tl = tk.Label(widget_frame, text=runway_title_readable, bg=lightest_grey, font=("Arial", 12, "bold"), anchor="w")
        bl = tk.Label(widget_frame, text=runway_airplane_readable, bg=lightest_grey, font=("Arial", 10, "bold"), anchor="w")

        tl.grid(row=0, column=0, sticky="w")
        bl.grid(row=2, column=0, sticky="w")



        # Other Right Side Label
        br = tk.Label(widget_frame, text=emergency_readable, bg=lightest_grey, fg=emergency_text_color, font=("Arial", 12, "bold"), anchor="e")
        br.grid(row=2, column=1, sticky="e")
        
        progress.pack(fill="both", expand=True)
        progress['value'] = 25 # Placeholder for simulation data

        # Make widget clickable (need to exclude the buttons in button_frame)
        def on_click(event):
            runway_selected(runway_title_readable, runway)

        widget_frame.bind("<Button-1>", on_click)
        for label in (tl, bl, br):
            label.bind("<Button-1>", on_click)
       
    # Creates the widget which shows all the information about the airplane selected
    def airplane_info_widget(display_frame, airplane):
        # Frame the information is shown in
        info_frame = tk.Frame(display_frame, bg = lightest_grey)
        info_frame.place(x=0, y= 30, relwidth=1, relheight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        info_row(info_frame, "Callsign: ", airplane.callsign, 0)
        info_row(info_frame, "Operator: ", airplane.operator, 1)
        info_row(info_frame, "Origin: ", airplane.origin, 2)
        info_row(info_frame, "Destination: ", airplane.destination, 3)
        info_row(info_frame, "Fuel Level (mins): ", airplane.fuelRemaining, 4)
        info_row(info_frame, "Altitude (m): ", airplane.altitude, 5)
        info_row(info_frame, "Ground Speed (kn): ", airplane.ground_speed, 6)
        info_row(info_frame, "Scheduled Arrival/Departure: ", format_time(airplane.scheduledTime), 7)
        info_row(info_frame, "Time in Queue ", "TODO: PLACEHOLDER", 8) #testing code: should pull from simulation

    # Creates the widget which shows all the information about the airplane selected
    def runway_info_widget(display_frame, runway):
        # Frame the information is shown in
        info_frame = tk.Frame(display_frame, bg = lightest_grey)
        info_frame.place(x=0, y= 30, relwidth=1, relheight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        info_row(info_frame, "Runway Name: ", "Runway " + str(runway.id), 0)
        info_row(info_frame, "Operating Mode: ", runway.mode, 1)
        info_row(info_frame, "Status: ", runway.status, 2)
        info_row(info_frame, "Time Idle", "TODO: PLACEHOLDER", 3) #testing code: should pull from simulation
        info_row(info_frame, "Landing: Take off Ratio ", "TODO: PLACEHOLDER", 4) #testing code: should pull from simulation

    # Function to generate a row of the display info
    def info_row(info_frame, label, attribute, row):
        label = tk.Label(info_frame, text = label, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify = "left", anchor = "w")
        label.grid(column = 0, row = row, sticky = "w")
        info =  tk.Label(info_frame, text = attribute, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify = "right", anchor = "e")
        info.grid(column = 1, row = row, sticky = "e")

    # Function to generate a row to input (used in simulation settings)
    def input_row(info_frame, label, row, default = ""):
        label = tk.Label(info_frame, text = label, bg=lightest_grey, font=("Arial", 13, "bold"), padx=5, justify = "left", anchor = "w")
        label.grid(column = 0, row = row, sticky = "w", padx= 5)
        default_value = tk.StringVar(value=default)
        input_box = tk.Entry(info_frame, width = 10, font=("Arial", 13, "bold"), justify = "left", textvariable=default_value)
        input_box.grid(column = 1, row = row, sticky = 'e', padx = 10, pady=5)
        return input_box
    
    # Called if an airplane button/widget is clicked
    def airplane_selected(airplane):
        display_info_frame = create_section(root, display_info_x_pos, y_pos_3_2, col_w_display, h_3_2, "Aircraft " + airplane.callsign)
        airplane_info_widget(display_info_frame, airplane)

    # Called if a runway button/widget is clicked
    def runway_selected(runway_readable, runway):
        display_info_frame = create_section(root,display_info_x_pos, y_pos_3_2, col_w_display, h_3_2, runway_readable)
        runway_info_widget(display_info_frame, runway)

    # Function to cycle through each operating mode
    def change_operating_mode(runway):
        if runway.mode == "LANDING":
            runway.mode = "MIXED"
        elif runway.mode == "MIXED":
            runway.mode = "TAKEOFF"
        else:
            runway.mode = "LANDING"
    
    # Function to fix widget children colors when updating parent widget color
    def update_widget_colors(widget, color):
        # Recursively updates the background of all standard Tkinter widgets.
        # Ignore ttk widgets (progress bars) and buttons
        if not isinstance(widget, (ttk.Progressbar, tk.Button)):
            widget.configure(bg=color)
        
        for child in widget.winfo_children():
            update_widget_colors(child, color)

    # Function to cycle through each status
    def change_status(runway, runway_widget, progress_container, pg_settings):
        # Determine the state
        if runway.status == "AVAILABLE":
            runway.status = "RUNWAY INSPECTION"
            new_bg, show_progress, relief_val, border_val = light_grey, False, "solid", 1
        elif runway.status == "RUNWAY INSPECTION":
            runway.status = "SNOW CLEARANCE"
            new_bg, show_progress, relief_val, border_val = light_grey, False, "solid", 1
        elif runway.status == "SNOW CLEARANCE":
            runway.status = "EQUIPMENT FAILURE"
            new_bg, show_progress, relief_val, border_val = light_grey, False, "solid", 1
        else:
            runway.status = "AVAILABLE"
            new_bg, show_progress, relief_val, border_val = lightest_grey, True, "flat", 0

        # 1. Update the main frame
        runway_widget.config(bg=new_bg, relief=relief_val, borderwidth=border_val)
        
        # 2. Use the recursive hunt to update all children
        update_widget_colors(runway_widget, new_bg)

        # 3. Toggle Progress Bar
        if show_progress:
            progress_container.grid(**pg_settings)
        else:
            progress_container.grid_forget()

    # Function that creates the popups for settings and statistics
    def create_popup(title):
        # Makes the entire screen black
        overlay = tk.Frame(root, bg="black")
        overlay.place(relx = 0, rely=0, relwidth = 1, relheight = 1)

        statistics_border = tk.Frame(overlay, bg = "white", width = window_w/3, height = window_h/2, relief = "solid", borderwidth = 2)
        statistics_border.place(relx = 0.5, rely = 0.5, anchor = "center")
        statistics_border.pack_propagate(False) # Statistics border no longer shrinks to the size of the text

        # Heading section containing both the title and the exit button
        header = tk.Frame(statistics_border, bg="white")
        header.pack(fill="x")
        tk.Button(header, width = 2, text="X", bg="#FFB8B8", fg = "#ff0000", relief="flat", justify= "left", command=lambda: close_popup(overlay)).pack(side="right", anchor="ne", padx = 4, pady=4)
        tk.Label(header, text=title, bg="white", font=("Arial", 14, "bold")).pack(pady=4, padx = 4, anchor = "w")

        info_frame = tk.Frame(statistics_border, bg=lightest_grey, width=window_w/3, height=window_h/2)
        info_frame.pack(fill="both", expand=True, padx=4, pady=4)
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)
        return info_frame

    #TODO: Function to pause the simulation
    def pause():
        pass
    
    # Function that generates the simulation settings box with all the inputs necessary
    def create_simulation_settings():
        info_frame = create_popup("Simulation Settings")

        number_of_runways = input_row(info_frame, "Number Of Runways: ", 0)
        inbound_flow = input_row(info_frame, "Inbound flow (aircraft per hour): ", 1)
        outbound_flow = input_row(info_frame, "Outbound flow (aircraft per hour): ", 2)
        speed_multiplier = input_row(info_frame, "Simulation speed multiplier: ", 3, 1.0)
        max_wait_time = input_row(info_frame, "Maximum take off wait time (minutes): ", 4, 30.0)
        min_fuel_level = input_row(info_frame, "Minimum fuel levels (minutes' worth): ", 5, 10.0)

        apply_changes_button = tk.Button(info_frame, font=("Arial", 13, "bold"), text="Apply Changes", bg="white", relief="solid", justify= "left", command=lambda: 
                                         apply_changes(number_of_runways.get(), inbound_flow.get(), outbound_flow.get(), speed_multiplier.get(), max_wait_time.get(), min_fuel_level.get()))
        apply_changes_button.grid(column = 0, row = 6, columnspan=2, padx = 10, pady=20)

    # Function that generates the statistics box with data pulled from the statistics class.
    def create_statistics():
        info_frame = create_popup("Statistical Report")

        statistics = Statistics() #testing code: temporary statistics
        report_data = statistics.report()

        info_row(info_frame, "Maximum holding queue size: ", report_data["maxHoldingQueue"], 0)
        info_row(info_frame, "Average holding queue size ", report_data["avgHoldingQueue"], 1)
        info_row(info_frame, "Maximum holding queue wait time (minutes) ", report_data["maxArrivalDelay"], 2)
        info_row(info_frame, "Average holding queue wait time (minutes) ", report_data["avgHoldingTime"], 3)
        info_row(info_frame, "Maximum take off queue size ", report_data["maxTakeoffQueue"], 4)
        info_row(info_frame, "Average take off queue size", report_data["avgArrivalDelay"], 5)
        info_row(info_frame, "Maximum take off queue wait time (minutes) ", report_data["maxHoldingQueue"], 6)
        info_row(info_frame, "Average take off queue wait time (minutes) ", report_data["avgTakeoffWait"], 7)
        info_row(info_frame, "Total inbound diversions ", report_data["diversions"], 8)
        info_row(info_frame, "Total outbound cancellations ", report_data["cancellations"], 9)
        info_row(info_frame, "Total simulation time ", "100", 10)

    # Function to remove the settings/statistics popup
    def close_popup(overlay):
        overlay.destroy()

    #TODO: function that resets the simulation
    def reset_simulation():
        pass

    # Turns a 4 digit integer into a HH:MM formatted string timestamp
    def format_time(time):
        return f"{time:04d}"[:2] + ":" + f"{time:04d}"[2:]
    
    def apply_changes(number_of_runways, inbound_flow, outbound_flow, speed_multiplier, max_wait_time, min_fuel_level):
        # TODO: here will be the code to update the simulation paramters
        pass
    
    # Take-off Queue Column
    x_pos = margin_x
    takeoff_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Take-off Queue", scrollable = True)

    #Testing code: would actually loop through the real takeoff queue
    for x in range(20):
        test_plane = Aircraft("1", "OUTBOUND", 1200, 30)
        create_plane_widget(takeoff_queue_frame, test_plane)
   
    # Holding Queue Column
    x_pos += col_w_standard + gap
    holding_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Holding Queue", scrollable = True)
    
    #Testing code: would actually loop through the real holding queue
    for x in range(7):
        test_plane = Aircraft("1", "INBOUND", 1201, 30)
        create_plane_widget(holding_queue_frame, test_plane)
   
    # Display Area
    x_pos += col_w_standard + gap
    create_section(root, x_pos, margin_y, col_w_display, col_w_display, "Display", title = False)
    
    # display info constants
    display_info_x_pos = x_pos
    y_pos_3_2 = margin_y + col_w_display + gap
    h_3_2 = top_col_h - col_w_display - gap

    # Default/nothing clicked display area
    display_info_frame = create_section(root, x_pos, y_pos_3_2, col_w_display, h_3_2, "Nothing Selected - Click on an Aircraft \n or Runway")
    info_frame = tk.Frame(display_info_frame, bg = lightest_grey)
    info_frame.place(x=0, y= 52, relwidth=1, relheight=1)

    # Runways Column
    x_pos += col_w_display + gap
    runway_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Runways", scrollable = True)
    #Testing code: would actually loop through each runway
    for x in range(20):
        test_plane = Aircraft("1", "INBOUND", 1201, 5000)
        test_runway = Runway(x, "MIXED", "AVAILABLE")
        if (x%2==0):
            test_runway.currentAircraft = test_plane
        create_runway_widget(runway_queue_frame, test_runway)
   
    # Control Panel
    panel_w = window_w - (2 * margin_x)
    panel_y = window_h - margin_y - panel_h
    control_panel_frame = create_section(root, margin_x, panel_y, panel_w, panel_h, "Control Panel", title = False)
    
    #testing code: placeholder time, should pull from simulation
    time = tk.Label(control_panel_frame, text=format_time(1159), bg=lightest_grey, fg=text_color, font=("Arial", 14, "bold"))
    time.grid(column = 0, row = 0, sticky = "w", padx = 5, pady = 5)

    pause_button = tk.Button(control_panel_frame, text="Pause [P]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: pause())
    pause_button.grid(column = 1, row = 0, sticky = "w", padx = 5, pady = 5)

    simulation_settings_button = tk.Button(control_panel_frame, text="Simulation Settings [S]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: create_simulation_settings())
    simulation_settings_button.grid(column = 2, row = 0, sticky = "w", padx = 5, pady = 5)

    view_statistics_button = tk.Button(control_panel_frame, text="View Statistics [V]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: create_statistics())
    view_statistics_button.grid(column = 3, row = 0, sticky = "w", padx = 5, pady = 5)

    reset_simulation_button = tk.Button(control_panel_frame, text="Reset Simulation [R]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: reset_simulation())
    reset_simulation_button.grid(column = 4, row = 0, sticky = "w", padx = 5, pady = 5)
    
    # Starts the simulation by showing the settings first. 
    create_simulation_settings()
    # Run application
    root.mainloop()

if __name__ == "__main__":
    create_ui()
