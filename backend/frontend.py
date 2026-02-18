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

# Will next week:
# progress bars
# plane/runway display
# display caption
# button images
# plane animation

import tkinter as tk
from aircraft import Aircraft
from runway import Runway
from statistics import Statistics
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
   
    root.title("Airport Simulation")
    root.geometry(f"{window_w}x{window_h}")
    root.configure(bg=dark_grey)

    root.bind("P", lambda x: pause())
    root.bind("p", lambda x: pause())
    root.bind("S", lambda x: create_simulation_settings())
    root.bind("s", lambda x: create_simulation_settings())
    root.bind("<Tab>", lambda x: create_statistics())
    root.bind("R", lambda x: reset_simulation())
    root.bind("r", lambda x: reset_simulation())
    #root.resizable(False, False)

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
        scrollbar = tk.Scrollbar(inner_frame, orient="vertical", command=canvas.yview)

        scrollable_inner_frame = tk.Frame(canvas, bg=light_grey)
        scrollable_inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=scrollable_inner_frame, anchor="nw")

        def resize_scrollable_frame(event):
            canvas.itemconfig(window, width=event.width)

        canvas.bind("<Configure>", resize_scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.place(x=0, y=40, relwidth=1, height=inner_h - 40)
        scrollbar.place(relx=1, y=40, anchor="ne", height=inner_h - 40)

        return scrollable_inner_frame

    # Helper function to create each plane widget (created as a button)
    def create_plane_widget(queue_column, plane):
        # Text to be shown to the user in each widget
        plane_info = (plane.callsign + "\n" + plane.operator + "\nScheduled " + format_time(plane.scheduledTime) + "\n")

        # Creates and places the widget
        plane_label = tk.Button(queue_column, text=plane_info, bg=lightest_grey, font=("Arial", 10), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: airplane_selected(plane))
        plane_label.pack(fill="x", pady=4, padx=(4, 22))

    # Helper function to create each runway widget (created as a button)
    def create_runway_widget(runway_column, runway):
        # Turns runway and airport attributes into a more readable, user-friendly format
        if runway.mode == "LANDING":
            runway_readable = "Runway "+ str(runway.id) + " - Landing only"
        elif runway.mode == "TAKEOFF":
            runway_readable = "Runway "+ str(runway.id) + " - Take off only"
        else:
            runway_readable = "Runway "+ str(runway.id) + " - Mixed Use"

        if runway.currentAircraft == None:
            airplane_readable = "Not currently in use"
        else:
            if runway.currentAircraft.type == "INBOUND":
                airplane_readable = runway.currentAircraft.callsign + " - Landing"
            else: 
                airplane_readable = runway.currentAircraft.callsign + " - Taking off"
        # Text to be shown to the user in each widget
        runway_info = runway_readable + "\n" + airplane_readable + "\n"

        # Container frame (acts as the widget row)
        runway_widget = tk.Frame(runway_column, bg=lightest_grey)
        runway_widget.pack(fill="x", pady=4, padx=(4, 22))

        # Main runway button
        main_button = tk.Button(runway_widget, text=runway_info, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify="left", anchor="w", relief="flat", command=lambda: runway_selected(runway_readable, runway))
        main_button.pack(side="left", fill="x", expand=True)

        # change operating mode button
        operating_mode = tk.Button(runway_widget, text="B", bg=lightest_grey, padx=5, relief="solid", command=lambda: change_operating_mode(runway))
        operating_mode.pack(side="right", anchor="ne", padx = 5, pady = 5)

        # change status button
        status_button = tk.Button(runway_widget, text="A", bg=lightest_grey, padx=5, relief="solid", command=lambda: change_status(runway, runway_widget, main_button))
        status_button.pack(side="right", anchor="ne", padx = 1, pady = 5)
       
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
    
    # Function to cycle through each status
    def change_status(runway, runway_widget, main_button):
        if runway.status == "AVAILABLE":
            runway.status = "RUNWAY INSPECTION"
            main_button.config(bg = light_grey,)
            runway_widget.config(bg = light_grey, relief = "solid", borderwidth = 1)
        elif runway.status == "RUNWAY INSPECTION":
            runway.status = "SNOW CLEARANCE"
        elif runway.status == "SNOW CLEARANCE":
            runway.status = "EQUIPMENT FAILURE"
        else:
            runway.status = "AVAILABLE"
            main_button.config(bg = lightest_grey)
            runway_widget.config(bg = lightest_grey, relief = "flat", borderwidth = 0)

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

    view_statistics_button = tk.Button(control_panel_frame, text="View Statistics [Tab]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: create_statistics())
    view_statistics_button.grid(column = 3, row = 0, sticky = "w", padx = 5, pady = 5)

    reset_simulation_button = tk.Button(control_panel_frame, text="Reset Simulation [R]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: reset_simulation())
    reset_simulation_button.grid(column = 4, row = 0, sticky = "w", padx = 5, pady = 5)
    
    # Starts the simulation by showing the settings first. 
    create_simulation_settings()
    # Run application
    root.mainloop()

if __name__ == "__main__":
    create_ui()
