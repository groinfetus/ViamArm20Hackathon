"""Test tape detection on a saved image, no arm or Viam needed.
   python test_vision.py scan.png
If tape_color.json doesn't exist yet, you'll be asked to click the tape in the image.
Writes mask.png and preview.png. Tune config.py until green paths sit on the tape centerline
and nothing else is detected."""
import os, sys, json
import cv2
import config
from vision import detect_tape_paths, draw_overlay, sample_tape_color

frame = cv2.imread(sys.argv[1] if len(sys.argv) > 1 else "scan.png")

if os.path.exists(config.TAPE_COLOR_FILE):
    ref = json.load(open(config.TAPE_COLOR_FILE))["lab"]
else:
    pts = []
    def cb(e, x, y, *_):
        if e == cv2.EVENT_LBUTTONDOWN:
            pts.append((x, y)); cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)
    cv2.namedWindow("click tape, Enter = done"); cv2.setMouseCallback("click tape, Enter = done", cb)
    while True:
        cv2.imshow("click tape, Enter = done", frame)
        if cv2.waitKey(20) in (13, 10) and pts: break
    cv2.destroyAllWindows()
    ref = sample_tape_color(frame, pts)
    json.dump({"lab": ref}, open(config.TAPE_COLOR_FILE, "w"))
    frame = cv2.imread(sys.argv[1] if len(sys.argv) > 1 else "scan.png")

paths, mask = detect_tape_paths(frame, ref)
print(f"{len(paths)} path(s):")
for i, p in enumerate(paths, 1):
    print(f"  {i}: {len(p)} waypoints, start={tuple(round(v) for v in p[0])}, "
          f"end={tuple(round(v) for v in p[-1])}")
prev = draw_overlay(frame, paths, mask)
cv2.imwrite("mask.png", mask); cv2.imwrite("preview.png", prev)
cv2.imshow("preview (any key)", prev); cv2.waitKey(0)
