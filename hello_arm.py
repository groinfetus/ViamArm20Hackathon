"""First-motion test: connect, print position, nudge up 20 mm, come back.
Run from the project folder:  python hello_arm.py
Keep a hand on the e-stop and the area around the arm clear."""
import asyncio
from viam.components.arm import Arm
from viam.proto.common import Pose
import config
from common import connect

NUDGE_MM = 20.0


async def main():
    robot = await connect()
    try:
        arm = Arm.from_robot(robot, config.ARM_NAME)

        start = await arm.get_end_position()
        print(f"Current position (mm): x={start.x:.1f} y={start.y:.1f} z={start.z:.1f}")
        print(f"Orientation: o=({start.o_x:.2f}, {start.o_y:.2f}, {start.o_z:.2f}) theta={start.theta:.1f}")

        input(f"\nEnter to move UP {NUDGE_MM:.0f} mm (Ctrl-C to abort)...")
        up = Pose(x=start.x, y=start.y, z=start.z + NUDGE_MM,
                  o_x=start.o_x, o_y=start.o_y, o_z=start.o_z, theta=start.theta)
        await arm.move_to_position(up)
        print("Moved up.")

        input("Enter to move back down to the start position...")
        await arm.move_to_position(start)
        print("Back at start. Arm connection works.")
    finally:
        await robot.close()


asyncio.run(main())
