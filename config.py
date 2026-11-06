# ---------- Viam connection (copy from the "Connect" tab in the Viam app) ----------
VIAM_ADDRESS = "armfarm20-main.310sld03v2.viam.cloud"
API_KEY = "61kd7qk80cg3slr9hvis5q9zm9hmwtg5"
API_KEY_ID = "ea0134ac-c55c-46d5-8ce5-e27a47284a74"
ARM_NAME = "arm"      # component names as configured in Viam
CAM_NAME = "cam"      # the realsense color camera
CAM_COLOR_SOURCE = "color"   # name of its color stream (test_camera.py prints what it returns)

# ---------- Servo server running on the Pi (servo_server.py) ----------
SERVO_URL = "http://PI_IP_ADDRESS:8000"
STOP_US = 1500        # tune: pulse width where YOUR servo stops
FORWARD_US = 1600     # tune: direction that pushes material out
REVERSE_US = 1400     # small backward pulse to relieve pressure

# ---------- Dispensing behavior ----------
PRE_FLOW_S = 0.4      # run extruder this long before arm starts moving
RETRACT_S = 0.15      # reverse pulse length after each bead
HOVER_MM = 30.0       # travel height above desk

# ---------- Safety box, arm base frame, mm. EDIT to your workspace ----------
BOUNDS = {"x": (150, 500), "y": (-300, 300), "z_max": 400}

# ---------- Files ----------
SCAN_POSE_FILE = "scan_pose.json"
CALIB_FILE = "calib.json"

# ---------- Tape detection (vision.py) ----------
TAPE_TOL = 35           # how far (LAB distance) a pixel may be from the taught tape color.
                        #   raise if tape is only partly detected, lower if other things leak in
LIGHTNESS_WEIGHT = 0.5  # <1 = care more about color than brightness (tolerates shadows)
MIN_ASPECT = 5          # tape must be at least this many times longer than wide
TAPE_COLOR_FILE = "tape_color.json"   # written by: python calibrate.py tape
MARGIN_PX = 15          # ignore this many pixels at the image border
MIN_AREA_PX = 400       # ignore specks smaller than this
MIN_PATH_LEN_PX = 60    # ignore tape pieces shorter than this
SIMPLIFY_EPS_PX = 3.0   # path simplification; higher = fewer waypoints, rougher curves
EXTEND_ENDS = True      # extend each path by half the tape width so it covers the tape ends
