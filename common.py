import asyncio, json
from viam.robot.client import RobotClient
from viam.proto.component.arm import JointPositions
import config
from vision import viam_to_bgr


async def connect():
    opts = RobotClient.Options.with_api_key(
        api_key=config.API_KEY, api_key_id=config.API_KEY_ID
    )
    return await RobotClient.at_address(config.VIAM_ADDRESS, opts)


async def grab_frame(cam):
    img = await cam.get_image()
    return viam_to_bgr(img)


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def load_json(path):
    with open(path) as f:
        return json.load(f)


async def move_to_scan_pose(arm):
    joints = load_json(config.SCAN_POSE_FILE)["joints"]
    await arm.move_to_joint_positions(JointPositions(values=joints))
    await asyncio.sleep(1.5)  # let vibration settle so the image isn't blurry
