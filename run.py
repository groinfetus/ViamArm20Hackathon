"""
python run.py --dry-run   # detect + preview only, arm only goes to scan pose
python run.py             # preview, confirm, then dispense
python run.py --yes       # skip the confirm prompt
"""
import argparse, asyncio
import numpy as np
import cv2
from viam.components.arm import Arm
from viam.components.camera import Camera
from viam.proto.common import Pose
import config, servo
from common import connect, grab_frame, load_json, move_to_scan_pose
from vision import detect_tape_paths, pix_to_arm, order_paths, draw_overlay


def in_bounds(x, y):
    b = config.BOUNDS
    return b["x"][0] <= x <= b["x"][1] and b["y"][0] <= y <= b["y"][1]


async def main(dry_run, yes):
    calib = load_json(config.CALIB_FILE)
    H = np.array(calib["H"])
    tape_lab = load_json(config.TAPE_COLOR_FILE)["lab"]   # python calibrate.py tape
    desk_z = calib["desk_z"]
    orient = calib["orientation"]
    hover_z = desk_z + config.HOVER_MM
    assert hover_z <= config.BOUNDS["z_max"]

    def pose(xy, z):
        return Pose(x=xy[0], y=xy[1], z=z, **orient)

    robot = await connect()
    try:
        arm = Arm.from_robot(robot, config.ARM_NAME)
        cam = Camera.from_robot(robot, config.CAM_NAME)

        await move_to_scan_pose(arm)
        frame = await grab_frame(cam)
        paths_px, mask = detect_tape_paths(frame, tape_lab)
        print(f"Detected {len(paths_px)} tape path(s)")

        cur = await arm.get_end_position()
        paths_arm = [[pix_to_arm(u, v, H) for u, v in p] for p in paths_px]
        paths_arm = order_paths(paths_arm, (cur.x, cur.y))

        bad = [p for p in paths_arm if not all(in_bounds(x, y) for x, y in p)]
        if bad:
            raise SystemExit(f"{len(bad)} path(s) outside BOUNDS, aborting")

        # preview shows detection order; the arm may run paths in a different (nearest-first) order
        preview = draw_overlay(frame, paths_px, mask)
        cv2.imwrite("preview.png", preview)
        cv2.imshow("detected tape (any key to continue)", preview)
        cv2.waitKey(0); cv2.destroyAllWindows()

        if dry_run or not paths_arm:
            return
        if not yes:
            input("Enter to start dispensing (Ctrl-C to abort)...")

        try:
            for path in paths_arm:
                await arm.move_to_position(pose(path[0], hover_z))
                await arm.move_to_position(pose(path[0], desk_z))
                servo.on()
                await asyncio.sleep(config.PRE_FLOW_S)
                for pt in path[1:]:
                    await arm.move_to_position(pose(pt, desk_z))
                servo.off()
                servo.retract()
                await arm.move_to_position(pose(path[-1], hover_z))
        finally:
            servo.off()  # always stop extruding, even on error
        await move_to_scan_pose(arm)
    finally:
        await robot.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.dry_run, a.yes))
