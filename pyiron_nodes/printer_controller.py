import serial
import time

class PrinterController:
    def __init__(self, port="COM4", baud=115200, simulate=True):
        self.port = port
        self.baud = baud
        self.simulate = simulate
        self.ser = None

    def connect(self):
        if self.simulate:
            print(f"[PrinterController] SIMULATION: Pretending to connect {self.port} @ {self.baud}")
            return True
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(2)
            print(f"[PrinterController] Connected to {self.port} @ {self.baud}")
            return True
        except Exception as e:
            print(f"[PrinterController] ERROR: {e}")
            return False

    def send_gcode(self, command):
        if self.simulate:
            print(f"[PrinterController] SIMULATION: {command}")
            return
        if self.ser:
            self.ser.write((command + "\n").encode())
            self.ser.flush()
            print(f"[PrinterController] Sent: {command}")

    def safe_park(self):
        self.send_gcode("G28")
        self.send_gcode("G1 X0 Y200 Z150 F3000")
        print("[PrinterController] Moved to safe park position")

    def disconnect(self):
        if self.ser:
            self.ser.close()
            print("[PrinterController] Disconnected")
