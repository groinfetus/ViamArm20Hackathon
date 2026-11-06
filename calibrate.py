"""
Usage (run from your laptop):
  python calibrate.py pose    # 1) jog arm to scan pose in the Viam app, then run this to save it
  python calibrate.py calib   # 2) click dots in the image, then touch each with the nozzle/pen
  python calibrate.py tape    # 3) click on your tape to teach it the tape color
"""
import asyncio, sys
import numpy as np
import cv2
from viam.components.arm import Arm
from viam.components.camera import Camera
import config
from common import connect, grab_frame, save_json, move_to_scan_pose
from vision import sample_tape_color


def click_points(frame, min_pts=4):
    pts = []
    disp = frame.copy()

    def cb(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            pts.append((x, y))
            cv2.circle(disp, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(disp, str(len(pts)), (x + 8, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 255), 2)

    cv2.namedWindow("click dots (Enter = done)")
    cv2.setMouseCallback("click dots (Enter = done)", cb)
    while True:
        cv2.imshow("click dots (Enter = done)", disp)
        if cv2.waitKey(20) in (13, 10) and len(pts) >= min_pts:
            break
    cv2.destroyAllWindows()
    return pts


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    robot = await connect()
    try:
        arm = Arm.from_robot(robot, config.ARM_NAME)
        cam = Camera.from_robot(robot, config.CAM_NAME)

        if cmd == "pose":
            joints = list(await arm.get_joint_positions())  # may be .values on some SDKs
            save_json(config.SCAN_POSE_FILE, {"joints": joints})
            print("Saved scan pose:", joints)

        elif cmd == "calib":
            print("Moving to scan pose (clear the area!)")
            await move_to_scan_pose(arm)
            frame = await grab_frame(cam)
            cv2.imwrite("scan.png", frame)
            pix = click_points(frame)          # click 4-6 dots, spread out

            arm_xy, zs, last = [], [], None
            for i, (u, v) in enumerate(pix):
                input(f"Dot {i+1}: jog nozzle tip onto it in the Viam app, press Enter...")
                p = await arm.get_end_position()
                arm_xy.append([p.x, p.y]); zs.append(p.z); last = p

            src = np.array(pix, dtype=np.float32)
            dst = np.array(arm_xy, dtype=np.float32)
            H, _ = cv2.findHomography(src, dst, 0)

            proj = cv2.perspectiveTransform(src.reshape(-1, 1, 2), H).reshape(-1, 2)
            errs = np.linalg.norm(proj - dst, axis=1)
            print("Per-point error (mm):", np.round(errs, 2), "max:", errs.max().round(2))
            if errs.max() > 3:
                print("WARNING: >3 mm error. Re-do the worst point or add more dots.")

            save_json(config.CALIB_FILE, {
                "H": H.tolist(),
                "desk_z": float(np.mean(zs)),
                "orientation": {"o_x": last.o_x, "o_y": last.o_y,
                                "o_z": last.o_z, "theta": last.theta},
            })
            print("Saved", config.CALIB_FILE)
        elif cmd == "tape":
            await move_to_scan_pose(arm)
            frame = await grab_frame(cam)
            cv2.imwrite("scan.png", frame)
            print("Click 3-5 spots ON the tape (inside it, not the edge), then Enter.")
            pts = click_points(frame, min_pts=3)
            lab = sample_tape_color(frame, pts)
            save_json(config.TAPE_COLOR_FILE, {"lab": lab})
            print("Saved tape color", [round(v) for v in lab], "->", config.TAPE_COLOR_FILE)
        else:
            print(__doc__)
    finally:
        await robot.close()


asyncio.run(main())
