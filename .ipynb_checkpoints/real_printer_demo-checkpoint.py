from pyiron_nodes.printer_controller import PrinterController

printer = PrinterController(port="COM4", baud=115200, simulate=False)
printer.connect()

printer.send_gcode("G28")               # Home all
printer.send_gcode("G1 Z15 F3000")      # Lift Z

printer.send_gcode("G1 X0 Y0 F3000")    # Top-left
printer.send_gcode("G1 X220 Y0 F3000")  # Top-right
printer.send_gcode("G1 X0 Y220 F3000")  # Bottom-left
printer.send_gcode("G1 X220 Y220 F3000")# Bottom-right
