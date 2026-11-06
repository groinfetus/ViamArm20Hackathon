"""Runs ON THE PI. Tiny HTTP server that sets the continuous-rotation servo pulse.
Start pigpio first:  sudo pigpiod
Then:                python3 servo_server.py
NOTE: pigpio does not work on Raspberry Pi 5. If you have a Pi 5, swap in gpiozero/lgpio.
No auth: only use on a trusted/hackathon network.
"""
import signal, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import pigpio

PIN = 12          # hardware-PWM-capable GPIO
PORT = 8000
pi = pigpio.pi()
if not pi.connected:
    sys.exit("pigpiod not running: sudo pigpiod")


def release():
    pi.set_servo_pulsewidth(PIN, 0)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/pulse":
            us = int(parse_qs(u.query)["us"][0])
            us = max(1000, min(2000, us))          # clamp for safety
            pi.set_servo_pulsewidth(PIN, us)
        elif u.path == "/stop":
            release()
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def shutdown(*_):
    release(); pi.stop(); sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)
release()
print(f"Servo server on :{PORT}, pin {PIN}")
HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
