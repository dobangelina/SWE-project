#this file is temporarily in backend as we dont have a working main.py (yet) and other files need to be accessed

#TODO: (in priority order)
## rework to fit all screen sizes
## airplane queue widgets
## runway queue widgets
## widget for airplane data
## clickable airplane widgets
## widget for runway data
## clickable runway widgets
## nothing selected + default screen
## control centre visuals
# scrolling
# aircraft failure error messages
# change runway modes
# control centre functionality 
# control centre keyboard access
# additional info on aircraft widgets
# link with backend
# progress bars
# plane/runway images and bg
# plane animation


import tkinter as tk
from aircraft import Aircraft
from runway import Runway

def create_ui():
    root = tk.Tk()

    # --- Configuration Variables ---
    # Dimensions
    window_w = root.winfo_screenwidth() - 100
    window_h = root.winfo_screenheight() - 100

    # Margins and gaps
    margin_x = window_w / 96
    margin_y = window_h / 54
    gap = window_w / 120
   
    # Width of boxes
    col_w_standard = window_w * (7/32)
    col_w_display = window_w * (143/480)
    panel_h = window_h * (11/180)
   
    # Calculated height for top columns
    top_col_h = window_h - (2 * margin_y) - panel_h - gap
   
    # Colors
    dark_grey = "#2b2b2b"       # Window background
    medium_grey = "#404040"     # Outer Section background (the 4px border on each section)
    light_grey = "#5c5c5c"      # Inset Section background
    lightest_grey = "#A6A4A4"
    text_color = "#000000"
   
    # --- Window Setup ---
    root.title("Control Interface")
    root.geometry(f"{window_w}x{window_h}")
    root.configure(bg=dark_grey)
    #root.resizable(False, False)

    # Helper function to create sections with inset rectangles
    def create_section(parent, x, y, w, h, name, title):
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
       
        # Now returns inner_frame for us, as that is where future widgets will go
        return inner_frame

    # Helper function to create each plane widget (created as a button)
    def create_plane_widget(queue_column, index, plane):
        widget_height = 60  #height of each plane widget 
        gap = 4 #gap between each plane widget

        # Text to be shown to the user in each widget
        plane_info = (plane.callsign + "\n" + plane.operator + "\nScheduled " + format_time(plane.scheduledTime))

        # Creates and places the widget
        plane_label = tk.Button(queue_column, text=plane_info, bg=lightest_grey, font=("Arial", 10), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: airplane_selected(plane))
        plane_label.place(x=0,y=40 + (index * (widget_height+gap)), relwidth=1, height=widget_height)

    # Helper function to create each runway widget (created as a button)
    def create_runway_widget(runway_column, index, runway):
        widget_height = 50  #height of each runway widget 
        gap = 4 #gap between each runway widget

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
        runway_info = runway_readable + "\n" + airplane_readable

        # Creates and places the widget
        plane_label = tk.Button(runway_column, text=runway_info, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: runway_selected(runway_readable, runway))
        plane_label.place(x=0,y=40 + (index * (widget_height+gap)), relwidth=1, height=widget_height)

    # Creates the widget which shows all the information about the airplane selected
    def airplane_info_widget(display_frame, airplane):
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
        info_row(info_frame, "Time in Queue ", "TODO: PLACEHOLDER", 8)

    # Creates the widget which shows all the information about the airplane selected
    def runway_info_widget(display_frame, runway):
        info_frame = tk.Frame(display_frame, bg = lightest_grey)
        info_frame.place(x=0, y= 30, relwidth=1, relheight=1)

        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        info_row(info_frame, "Runway Name: ", "Runway " + str(runway.id), 0)
        info_row(info_frame, "Operating Mode: ", runway.mode, 1)
        info_row(info_frame, "Status: ", runway.status, 2)
        info_row(info_frame, "Time Idle", "TODO: PLACEHOLDER", 3)
        info_row(info_frame, "Landing: Take off Ratio ", "TODO: PLACEHOLDER", 4)

    # Function to generate a row of the display info
    def info_row(info_frame, label, attribute, row):
        callsign_label = tk.Label(info_frame, text = label, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify = "left", anchor = "w")
        callsign_label.grid(column = 0, row = row, sticky = "w")
        callsign =  tk.Label(info_frame, text = attribute, bg=lightest_grey, font=("Arial", 10, "bold"), padx=5, justify = "right", anchor = "e")
        callsign.grid(column = 1, row = row, sticky = "e")
    
    # Called if an airplane button/widget is clicked
    def airplane_selected(airplane):
        display_info_frame = create_section(root,display_info_x_pos, y_pos_3_2, col_w_display, h_3_2, "Aircraft " + airplane.callsign, True)
        airplane_info_widget(display_info_frame, airplane)

    # Called if a runway button/widget is clicked
    def runway_selected(runway_readable, runway):
        display_info_frame = create_section(root,display_info_x_pos, y_pos_3_2, col_w_display, h_3_2, runway_readable, True)
        runway_info_widget(display_info_frame, runway)

    #TODO: function to pause the simulation
    def pause():
        pass

    def simulation_settings():
        pass
    
    def view_statistics():
        pass

    def reset_simulation():
        pass

    # Turns a 4 digit integer into a HH:MM formatted string timestamp
    def format_time(time):
        return f"{time:04d}"[:2] + ":" + f"{time:04d}"[2:]
    
    # --- Section Positioning ---
    # Take-off Queue Column
    x_pos = margin_x
    takeoff_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Take-off Queue", True)
    
    #Testing code: would actually loop through the real takeoff queue
    for x in range(6):
        test_plane = Aircraft("1", "OUTBOUND", 1200, 30)
        create_plane_widget(takeoff_queue_frame, x, test_plane)
   
    # Holding Queue Column
    x_pos += col_w_standard + gap
    holding_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Holding Queue", True)
    
    #Testing code: would actually loop through the real holding queue
    for x in range(7):
        test_plane = Aircraft("1", "INBOUND", 1201, 30)
        create_plane_widget(holding_queue_frame, x, test_plane)
   
    # Display Area
    x_pos += col_w_standard + gap
    create_section(root, x_pos, margin_y, col_w_display, col_w_display, "Display", False)
    
    # display info constants
    display_info_x_pos = x_pos
    y_pos_3_2 = margin_y + col_w_display + gap
    h_3_2 = top_col_h - col_w_display - gap

    # Default/nothing clicked display area
    display_info_frame = create_section(root, x_pos, y_pos_3_2, col_w_display, h_3_2, "Nothing Selected - Click on an Aircraft \n or Runway", True)
    info_frame = tk.Frame(display_info_frame, bg = lightest_grey)
    info_frame.place(x=0, y= 52, relwidth=1, relheight=1)

    # Runways Column
    x_pos += col_w_display + gap
    runway_queue_frame = create_section(root, x_pos, margin_y, col_w_standard, top_col_h, "Runways", True)
    #Testing code: would actually loop through each runway
    for x in range(10):
        test_plane = Aircraft("1", "INBOUND", 1201, 5000)
        test_runway = Runway(x, "MIXED", "AVAILABLE")
        if (x%2==0):
            test_runway.currentAircraft = test_plane
        create_runway_widget(runway_queue_frame, x, test_runway)
   
    # Control Panel
    panel_w = window_w - (2 * margin_x)
    panel_y = window_h - margin_y - panel_h
    control_panel_frame = create_section(root, margin_x, panel_y, panel_w, panel_h, "Control Panel", False)
    #placeholder time
    time = tk.Label(control_panel_frame, text=format_time(1159), bg=lightest_grey, fg=text_color, font=("Arial", 14, "bold"))
    time.grid(column = 0, row = 0, sticky = "w", padx = 5, pady = 5)

    pause_button = tk.Button(control_panel_frame, text="Pause [P]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: pause())
    pause_button.grid(column = 1, row = 0, sticky = "w", padx = 5, pady = 5)

    simulation_settings = tk.Button(control_panel_frame, text="Simulation Settings [S]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: simulation_settings())
    simulation_settings.grid(column = 2, row = 0, sticky = "w", padx = 5, pady = 5)

    view_statistics = tk.Button(control_panel_frame, text="View Statistics [Tab]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: view_statistics())
    view_statistics.grid(column = 3, row = 0, sticky = "w", padx = 5, pady = 5)

    reset_simulation = tk.Button(control_panel_frame, text="Reset Simulation [R]", bg=lightest_grey, font=("Arial", 10, "bold", "underline"), padx=5, justify = "left", anchor = "w", relief="flat", command=lambda: reset_simulation())
    reset_simulation.grid(column = 4, row = 0, sticky = "w", padx = 5, pady = 5)
    
    # Run application
    root.mainloop()

if __name__ == "__main__":
    create_ui()
