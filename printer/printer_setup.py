from .printer_controller import PrinterController

def send_gcode(command, port="COM4", baudrate=115200, simulate=True):
    printer = PrinterController(port=port, baud=baudrate, simulate=simulate)
    if printer.connect():
        printer.send_gcode(command)
        printer.disconnect()

def check_printer(port="COM4", baudrate=115200, simulate=True, safe_park=False):
    printer = PrinterController(port=port, baud=baudrate, simulate=simulate)
    connected = printer.connect()
    if connected and safe_park:
        printer.safe_park()
    printer.disconnect()
    return connected
