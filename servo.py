"""Client for servo_server.py. Used by run.py on your laptop (or the Pi)."""
import time
import urllib.request
import config


def _get(path):
    urllib.request.urlopen(config.SERVO_URL + path, timeout=2).read()


def on():
    _get(f"/pulse?us={config.FORWARD_US}")


def off():
    _get("/stop")


def retract():
    _get(f"/pulse?us={config.REVERSE_US}")
    time.sleep(config.RETRACT_S)
    _get("/stop")


if __name__ == "__main__":
    # bench test, no arm:  python servo.py
    on(); time.sleep(3); off(); time.sleep(1); retract()
